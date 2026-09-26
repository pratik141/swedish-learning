import { createAccountController } from "./modules/account.js";
import { createSituationsController } from "./modules/situations.js";

const state = {
  category: "",
  level: "all",
  set: "all",
  type: "all",
  query: "",
  view: "cards",
  tab: "vocabulary",
  speechRate: "0.82",
  theme: localStorage.getItem("theme") || "light",
};

const progressKey = "sprakverkstan-progress";
const dailyGoal = 10;
const progress = JSON.parse(localStorage.getItem(progressKey) || "null") || {
  favourites: [],
  learned: [],
  missed: [],
  reviewedToday: 0,
  reviewedDate: "",
  streak: 0,
  lastStudiedDate: "",
};

let accountController;
let situationsController;
let manifest = null;
let grammarGroups = [];
let grammarLoaded = false;
let activeItems = [];
let pronunciationItems = [];
let pronunciationLoading = false;
let reviewItems = [];
let activeHasMore = false;
let activeSelector = {};
let searchTimer;
let vocabularyLoadId = 0;

const els = {
  category: document.getElementById("categorySelect"),
  level: document.getElementById("levelSelect"),
  set: document.getElementById("setSelect"),
  type: document.getElementById("typeSelect"),
  search: document.getElementById("searchInput"),
  chips: document.getElementById("chapterChips"),
  cards: document.getElementById("cards"),
  tableWrap: document.getElementById("tableWrap"),
  tableBody: document.getElementById("tableBody"),
  visible: document.getElementById("visibleCount"),
  loadMoreWords: document.getElementById("loadMoreWords"),
  empty: document.getElementById("emptyState"),
  loading: document.getElementById("loadingState"),
  cardsView: document.getElementById("cardsView"),
  tableView: document.getElementById("tableView"),
  notes: document.getElementById("grammarNotes"),
  themeToggle: document.getElementById("themeToggle"),
  tabs: document.querySelectorAll(".study-tab"),
  panels: document.querySelectorAll(".tab-panel"),
  pronunciationList: document.getElementById("pronunciationList"),
  speechStatus: document.getElementById("speechStatus"),
  sentenceCard: document.getElementById("sentenceCard"),
  newSentence: document.getElementById("newSentence"),
  quizCard: document.getElementById("quizCard"),
  nextQuestion: document.getElementById("nextQuestion"),
  scoreValue: document.getElementById("scoreValue"),
  speechRate: document.getElementById("speechRate"),
  testMode: document.getElementById("testMode"),
  situationSelect: document.getElementById("situationSelect"),
  situationContent: document.getElementById("situationContent"),
  reviewCards: document.getElementById("reviewCards"),
  reviewEmpty: document.getElementById("reviewEmpty"),
  progressSummary: document.getElementById("progressSummary"),
  resetProgress: document.getElementById("resetProgress"),
};

const practice = { question: null, correct: 0, total: 0 };
const sentencePractice = { item: null, selected: [] };

function saveProgress() {
  localStorage.setItem(progressKey, JSON.stringify(progress));
  accountController?.scheduleProgressSync();
}

function hasProgress(list, id) {
  return list.includes(id);
}

function toggleProgress(list, id) {
  const index = list.indexOf(id);
  if (index === -1) list.push(id);
  else list.splice(index, 1);
  recordStudySession();
  saveProgress();
  render();
  renderReview();
}

function getDateKey(date) {
  return new Date(date).toISOString().slice(0, 10);
}

function recordStudySession() {
  const today = getDateKey(new Date());
  const previous = progress.lastStudiedDate;
  if (!previous) {
    progress.streak = 1;
  } else if (previous === today) {
    progress.streak = Math.max(progress.streak || 1, 1);
  } else {
    const previousDate = new Date(previous);
    const currentDate = new Date(today);
    const diffDays = Math.round((currentDate - previousDate) / 86400000);
    progress.streak = diffDays === 1 ? (progress.streak || 1) + 1 : 1;
  }
  progress.lastStudiedDate = today;
  saveProgress();
}

function markReviewed() {
  const today = getDateKey(new Date());
  if (progress.reviewedDate !== today) {
    progress.reviewedDate = today;
    progress.reviewedToday = 0;
  }
  progress.reviewedToday += 1;
  recordStudySession();
}

function norm(value) {
  return String(value || "")
    .toLocaleLowerCase("sv-SE")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function escapeHTML(value) {
  return String(value || "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[char]));
}

async function setup() {
  applyTheme(state.theme);
  accountController = createAccountController({ progress, render, renderReview });
  const accountReady = accountController.initialize();
  manifest = await fetchJSON("/api/manifest");
  state.category = manifest.chapters[0]?.slug || "all";

  els.category.innerHTML = [
    ...manifest.chapters.map((chapter) => (
      `<option value="${escapeHTML(chapter.slug)}">${escapeHTML(chapter.label)} (${chapter.count})</option>`
    )),
    '<option value="all">All categories</option>',
  ].join("");

  els.chips.innerHTML = [
    ...manifest.chapters.slice(0, 12).map((chapter) => (
      `<button class="chip" type="button" data-category="${escapeHTML(chapter.slug)}">${escapeHTML(chapter.label.split(" ").slice(0, 3).join(" "))}</button>`
    )),
    '<button class="chip" type="button" data-category="all">All</button>',
  ].join("");

  situationsController = createSituationsController({
    select: els.situationSelect,
    content: els.situationContent,
    speak,
    escapeHTML,
  });
  els.category.value = state.category;
  bindEvents();
  setTab(state.tab);
  await loadAndRender();
  await accountReady;
}

function renderGrammar() {
  els.notes.innerHTML = grammarGroups.map((section) => (
    `<section class="grammar-group"><div class="grammar-group-heading"><p class="eyebrow">Study group</p><h3>${escapeHTML(section.group)}</h3><p>${escapeHTML(section.intro)}</p></div><div class="grammar-lessons">${section.lessons.map((lesson) => {
      const examples = lesson.examples || [];
      const commonMistakes = lesson.commonMistakes || lesson.exceptions || [];
      const exercise = lesson.exercise || {
        prompt: `Choose the correct form for the rule in ${lesson.title}.`,
        options: [lesson.rule],
        answer: lesson.rule,
        explanation: "Practice the rule again and listen for the pattern in real sentence examples.",
      };
      const exerciseOptions = Array.isArray(exercise.options) && exercise.options.length ? exercise.options : [exercise.answer];
      return `<details class="note"><summary>${escapeHTML(lesson.title)}</summary><div class="grammar-block"><strong>Simple rule</strong><p>${escapeHTML(lesson.rule)}</p></div><div class="grammar-details"><div class="grammar-why"><strong>Why?</strong><p>${escapeHTML(lesson.why || "This pattern helps you make clear Swedish sentences.")}</p></div>${commonMistakes.length ? `<div class="grammar-exceptions"><strong>Common mistakes</strong><ul>${commonMistakes.map((mistake) => `<li>${escapeHTML(mistake)}</li>`).join("")}</ul></div>` : ""}${examples.length ? `<div class="grammar-examples"><strong>Examples</strong>${examples.map((example) => `<p><span class="swedish-example">${escapeHTML(example.sv)}</span><span>${escapeHTML(example.en)}</span></p>`).join("")}</div>` : ""}${exercise && exercise.prompt ? `<div class="grammar-exercise"><strong>Quick exercise</strong><p>${escapeHTML(exercise.prompt)}</p><div class="exercise-options">${exerciseOptions.map((option) => `<button type="button" class="exercise-option" data-gr-answer="${escapeHTML(option)}" data-gr-correct="${escapeHTML(exercise.answer || option)}" data-gr-explanation="${escapeHTML(exercise.explanation || "Try the rule again.")}">${escapeHTML(option)}</button>`).join("")}</div><p class="exercise-feedback" aria-live="polite"></p></div>` : ""}${lesson.source ? `<small class="grammar-source">Reference: <a href="${escapeHTML(lesson.source.url)}" target="_blank" rel="noreferrer">${escapeHTML(lesson.source.title)}</a> · ${escapeHTML(lesson.source.license)}</small>` : ""}</div></details>`;
    }).join("")}</div></section>`
  )).join("");
}

async function loadGrammar() {
  if (grammarLoaded) return;
  grammarGroups = await fetchJSON("/api/grammar");
  grammarLoaded = true;
  renderGrammar();
}

function bindEvents() {
  els.category.addEventListener("change", async (event) => {
    state.category = event.target.value;
    syncChips();
    await loadAndRender();
  });

  for (const [control, key] of [[els.level, "level"], [els.set, "set"], [els.type, "type"]]) {
    control.addEventListener("change", async (event) => {
      state[key] = event.target.value;
      await loadAndRender();
    });
  }

  els.search.addEventListener("input", () => {
    state.query = els.search.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadAndRender(), 250);
  });

  els.chips.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;
    state.category = button.dataset.category;
    els.category.value = state.category;
    syncChips();
    await loadAndRender();
  });

  els.loadMoreWords.addEventListener("click", async () => {
    els.loadMoreWords.disabled = true;
    try {
      const page = await fetchVocabularyPage(activeSelector, activeItems.length);
      activeItems.push(...page.items);
      activeHasMore = page.hasMore;
      render();
    } finally {
      els.loadMoreWords.disabled = false;
    }
  });

  els.cardsView.addEventListener("click", () => setView("cards"));
  els.tableView.addEventListener("click", () => setView("table"));
  els.cards.addEventListener("click", handleVocabularyPlay);
  els.tableWrap.addEventListener("click", handleVocabularyPlay);
  els.cards.addEventListener("click", handleProgressAction);
  els.tableWrap.addEventListener("click", handleProgressAction);
  els.reviewCards.addEventListener("click", handleProgressAction);
  els.notes.addEventListener("click", (event) => {
    const button = event.target.closest(".exercise-option");
    if (!button) return;
    const exerciseCard = button.closest(".grammar-exercise");
    const feedback = exerciseCard?.querySelector(".exercise-feedback");
    const isCorrect = button.dataset.grAnswer === button.dataset.grCorrect;
    exerciseCard?.querySelectorAll(".exercise-option").forEach((option) => { option.disabled = true; });
    if (feedback) {
      feedback.textContent = isCorrect
        ? `Correct: ${button.dataset.grAnswer}. ${button.dataset.grExplanation}`
        : `Correct answer: ${button.dataset.grCorrect}. ${button.dataset.grExplanation}`;
    }
  });
  els.themeToggle.addEventListener("click", () => {
    applyTheme(state.theme === "dark" ? "light" : "dark");
  });
  els.speechRate.addEventListener("change", (event) => { state.speechRate = event.target.value; });
  els.testMode.addEventListener("change", () => startPractice());
  els.tabs.forEach((tab) => tab.addEventListener("click", () => setTab(tab.dataset.tab)));
  els.newSentence.addEventListener("click", renderSentence);
  els.sentenceCard.addEventListener("click", (event) => {
    const playButton = event.target.closest("button[data-sentence-say]");
    if (playButton) {
      speak(playButton.dataset.sentenceSay);
      return;
    }
    const wordButton = event.target.closest("button[data-word]");
    if (wordButton) {
      sentencePractice.selected.push(wordButton.dataset.word);
      wordButton.remove();
      renderSentenceBuilder();
      return;
    }
    if (event.target.closest("#checkSentence")) checkSentence();
  });
  els.nextQuestion.addEventListener("click", () => {
    if (practice.question) renderQuizQuestion();
    else startPractice();
  });
  els.resetProgress.addEventListener("click", () => {
    progress.favourites = [];
    progress.learned = [];
    progress.missed = [];
    progress.reviewedToday = 0;
    saveProgress();
    render();
    renderReview();
  });
  els.pronunciationList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-say]");
    if (!button) return;
    speak(button.dataset.say);
  });
  if ("speechSynthesis" in window) {
    window.speechSynthesis.addEventListener("voiceschanged", () => {
      if (state.tab === "pronunciation") renderPronunciation();
    });
  }
}

function handleVocabularyPlay(event) {
  const button = event.target.closest("button[data-vocab-say]");
  if (!button) return;
  speak(button.dataset.vocabSay);
}

function handleProgressAction(event) {
  const button = event.target.closest("button[data-progress-action]");
  if (!button) return;
  const id = Number(button.dataset.wordId);
  toggleProgress(progress[button.dataset.progressAction], id);
}

function speechSupported() {
  return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function swedishVoice() {
  if (!speechSupported()) return null;
  return window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase() === "sv-se")
    || window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase().startsWith("sv"));
}

function speak(text) {
  const voice = swedishVoice();
  if (!voice) {
    els.speechStatus.textContent = speechSupported()
      ? "No Swedish voice is installed in this browser. Install a Swedish voice in your system speech settings, then reload."
      : "Speech audio is not available in this browser. Use the reading aid below each word.";
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = voice.lang;
  utterance.voice = voice;
  utterance.rate = Number(state.speechRate);
  utterance.pitch = 1;
  utterance.onstart = () => { els.speechStatus.textContent = `Playing Swedish pronunciation: ${text}`; };
  utterance.onerror = () => { els.speechStatus.textContent = "The browser could not play speech. Check your system audio or choose a browser with speech voices enabled."; };
  window.speechSynthesis.speak(utterance);
}

async function fetchJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
}

async function loadCategory(slug) {
  activeSelector = { category: slug };
  const response = await fetchVocabularyPage(activeSelector);
  activeHasMore = response.hasMore;
  return response.items;
}

async function loadActiveItems() {
  if (state.set === "quick") {
    activeSelector = { set: "quick" };
    const response = await fetchVocabularyPage(activeSelector);
    activeHasMore = response.hasMore;
    return response.items;
  }
  if (state.category === "all") return loadVocabularyStartPage();
  return loadCategory(state.category);
}

async function loadVocabularyStartPage() {
  activeSelector = { all: "true" };
  const response = await fetchVocabularyPage(activeSelector);
  activeHasMore = response.hasMore;
  return response.items;
}

async function fetchVocabularyPage(selector, offset = 0) {
  const params = new URLSearchParams({ limit: "50", offset: String(offset) });
  for (const [key, value] of Object.entries(selector)) params.set(key, value);
  if (state.level !== "all") params.set("level", state.level);
  if (state.type !== "all") params.set("kind", state.type);
  if (state.query.trim()) params.set("q", state.query.trim());
  return fetchJSON(`/api/vocabulary?${params}`);
}

async function loadAllPages(selector) {
  const items = [];
  let offset = 0;
  let page;
  do {
    page = await fetchVocabularyPage(selector, offset);
    items.push(...page.items);
    offset += page.items.length;
  } while (page.hasMore);
  return items;
}

async function loadReviewItems() {
  const ids = [...new Set([...progress.favourites, ...progress.missed])];
  if (!ids.length) {
    reviewItems = [];
    renderReview();
    return;
  }
  const items = [];
  for (let offset = 0; offset < ids.length; offset += 1000) {
    const page = await fetchVocabularyPage({ ids: ids.slice(offset, offset + 1000).join(",") });
    items.push(...page.items);
  }
  reviewItems = items;
  renderReview();
}

async function loadPronunciationItems() {
  if (pronunciationItems.length || pronunciationLoading) return;
  pronunciationLoading = true;
  els.speechStatus.textContent = "Loading pronunciation for all vocabulary words...";
  try {
    pronunciationItems = await loadAllPages({ all: "true" });
    renderPronunciation();
  } finally {
    pronunciationLoading = false;
  }
}

async function loadAndRender() {
  const loadId = ++vocabularyLoadId;
  els.loading.hidden = false;
  els.empty.hidden = true;
  els.cards.hidden = true;
  els.tableWrap.hidden = true;
  try {
    const items = await loadActiveItems();
    if (loadId !== vocabularyLoadId) return;
    activeItems = items;
    syncChips();
    render();
    if (state.tab === "pronunciation") await loadPronunciationItems();
    if (state.tab === "sentences") renderSentence();
    if (state.tab === "practice" && !practice.question) startPractice();
    if (state.tab === "situations") await situationsController.load();
  } finally {
    if (loadId === vocabularyLoadId) {
      els.loading.hidden = true;
      applyViewVisibility();
    }
  }
}

function syncChips() {
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.category === state.category);
  });
}

function setView(view) {
  state.view = view;
  els.cardsView.classList.toggle("active", view === "cards");
  els.tableView.classList.toggle("active", view === "table");
  els.cardsView.setAttribute("aria-pressed", view === "cards");
  els.tableView.setAttribute("aria-pressed", view === "table");
  applyViewVisibility();
  render();
}

function applyViewVisibility() {
  els.cards.hidden = state.view !== "cards";
  els.tableWrap.hidden = state.view !== "table";
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("theme", theme);
  els.themeToggle.textContent = theme === "dark" ? "Light theme" : "Dark theme";
  els.themeToggle.setAttribute("aria-pressed", theme === "dark");
}

function setTab(tab) {
  state.tab = tab;
  els.tabs.forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active);
  });
  els.panels.forEach((panel) => { panel.hidden = panel.dataset.panel !== tab; });
  if (tab === "grammar") loadGrammar().catch(showLearningLoadError);
  if (tab === "pronunciation") loadPronunciationItems();
  if (tab === "sentences") renderSentence();
  if (tab === "practice" && !practice.question) startPractice();
  if (tab === "review") loadReviewItems();
  if (tab === "situations") situationsController.load().catch(showLearningLoadError);
}

function showLearningLoadError(error) {
  els.empty.hidden = false;
  els.empty.textContent = "Could not load this study content. Please refresh the page.";
  console.error(error);
}

function filtered(items = activeItems) {
  const quickSet = new Set(manifest.quickIds);
  return items.filter((item) => {
    if (state.level !== "all" && item.level !== state.level) return false;
    if (state.type !== "all" && item.kind !== state.type) return false;
    if (state.set === "quick" && !quickSet.has(item.id)) return false;
    return true;
  });
}

function render() {
  const rows = filtered();
  els.visible.textContent = rows.length.toLocaleString();
  els.empty.hidden = rows.length !== 0;
  els.loadMoreWords.hidden = !activeHasMore || state.tab !== "vocabulary";
  if (state.view === "cards") renderCards(rows);
  if (state.view === "table") renderTable(rows);
}

function progressButtons(item) {
  const favouriteLabel = hasProgress(progress.favourites, item.id) ? "Unfavourite" : "Favourite";
  const learnedLabel = hasProgress(progress.learned, item.id) ? "Not learned" : "Mark learned";
  return `<div class="progress-actions"><button class="small-action ${hasProgress(progress.favourites, item.id) ? "selected" : ""}" type="button" data-progress-action="favourites" data-word-id="${item.id}">${favouriteLabel}</button><button class="small-action ${hasProgress(progress.learned, item.id) ? "selected" : ""}" type="button" data-progress-action="learned" data-word-id="${item.id}">${learnedLabel}</button></div>`;
}

function renderReview() {
  const current = new Set([...progress.favourites, ...progress.missed]);
  const items = reviewItems.filter((item) => current.has(item.id));
  const learnedCount = progress.learned.length;
  const today = getDateKey(new Date());
  const reviewedToday = progress.reviewedDate === today ? progress.reviewedToday : 0;
  const totalWords = reviewItems.length || manifest.meta.total;
  const goalPercent = Math.min(100, Math.round((reviewedToday / dailyGoal) * 100));
  const streakLabel = progress.streak || 0;
  const lastStudyLabel = progress.lastStudiedDate ? new Date(progress.lastStudiedDate).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";
  els.progressSummary.innerHTML = `<div class="progress-stat"><strong>${learnedCount} / ${totalWords}</strong><span>learned</span></div><div class="progress-stat"><strong>${progress.favourites.length}</strong><span>favourites</span></div><div class="progress-stat"><strong>${progress.missed.length}</strong><span>to revisit</span></div><div class="progress-stat"><strong>${reviewedToday} / ${dailyGoal}</strong><span>today's goal</span><div class="goal-track"><span style="width: ${goalPercent}%"></span></div></div><div class="progress-stat"><strong>${streakLabel}</strong><span>streak</span><small>Last: ${lastStudyLabel}</small></div>`;
  els.reviewEmpty.hidden = items.length !== 0;
  els.reviewCards.innerHTML = items.map((item) => (
    `<article class="vocab-card"><div class="card-meta"><span>${escapeHTML(item.categoryLabel)}</span><span class="badge">${hasProgress(progress.missed, item.id) ? "Missed" : "Favourite"}</span></div><div class="word-with-play"><div class="swedish">${escapeHTML(item.sv)}</div><button class="play-button" type="button" data-vocab-say="${escapeHTML(item.sv)}" aria-label="Play Swedish pronunciation for ${escapeHTML(item.sv)}">Play</button></div><div class="meaning"><div><strong>English:</strong> ${escapeHTML(item.en)}</div><div class="hindi"><strong>हिन्दी:</strong> ${escapeHTML(item.hi || "Not available")}</div></div>${progressButtons(item)}${item.example?.sv ? `<div class="example"><p><span>SV</span> ${escapeHTML(item.example.sv)}</p><p><span>EN</span> ${escapeHTML(item.example.en)}</p></div>` : ""}${item.source?.uri ? `<small class="data-source">Source: <a href="${escapeHTML(item.source.uri)}" target="_blank" rel="noreferrer">${escapeHTML(item.source.name)} · ${escapeHTML(item.source.license)}</a></small>` : ""}</article>`
  )).join("");
}

function renderCards(rows) {
  els.cards.innerHTML = rows.map((item) => (
    `<article class="vocab-card">
      <div class="card-meta"><span>${escapeHTML(item.categoryLabel)}</span><span class="badge">${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</span></div>
      <div class="word-with-play"><div class="swedish">${escapeHTML(item.sv)}</div><button class="play-button" type="button" data-vocab-say="${escapeHTML(item.sv)}" aria-label="Play Swedish pronunciation for ${escapeHTML(item.sv)}">Play</button></div>
      <div class="meaning">
        <div><strong>English:</strong> ${escapeHTML(item.en)}</div>
        <div class="hindi"><strong>हिन्दी:</strong> ${escapeHTML(item.hi || "Not available")}</div>
      </div>
      <div class="forms">${escapeHTML(item.forms || "")}</div>
      ${item.pron ? `<div class="pron">Reading aid: ${escapeHTML(item.pron)}</div>` : ""}
      ${item.source?.uri ? `<small class="data-source">Source: <a href="${escapeHTML(item.source.uri)}" target="_blank" rel="noreferrer">${escapeHTML(item.source.name)} · ${escapeHTML(item.source.license)}</a></small>` : ""}
      ${progressButtons(item)}
      ${item.example?.sv ? `<div class="example">
        <p><span>SV</span> ${escapeHTML(item.example.sv)}</p>
        <p><span>EN</span> ${escapeHTML(item.example.en)}</p>
        <p class="hindi"><span>HI</span> ${escapeHTML(item.example.hi)}</p>
      </div>` : ""}
    </article>`
  )).join("");
}

function renderTable(rows) {
  els.tableBody.innerHTML = rows.map((item) => (
    `<tr>
      <td><div class="table-word"><strong>${escapeHTML(item.sv)}</strong><button class="play-button" type="button" data-vocab-say="${escapeHTML(item.sv)}" aria-label="Play Swedish pronunciation for ${escapeHTML(item.sv)}">Play</button></div><small>${escapeHTML(item.categoryLabel)} · ${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</small>${item.source?.uri ? `<small class="data-source"><a href="${escapeHTML(item.source.uri)}" target="_blank" rel="noreferrer">${escapeHTML(item.source.name)} · ${escapeHTML(item.source.license)}</a></small>` : ""}${progressButtons(item)}</td>
      <td>${escapeHTML(item.en)}</td>
      <td class="hindi">${escapeHTML(item.hi || "Not available")}</td>
      <td>${escapeHTML(item.forms || "")}${item.pron ? `<br><small>Reading aid: ${escapeHTML(item.pron)}</small>` : ""}</td>
      <td>${item.example?.sv ? `<strong>SV</strong> ${escapeHTML(item.example.sv)}<br><strong>EN</strong> ${escapeHTML(item.example.en)}<br><span class="hindi"><strong>HI</strong> ${escapeHTML(item.example.hi)}</span>` : "No example available"}</td>
    </tr>`
  )).join("");
}

function sampleItems(limit = 8) {
  return filtered().filter((item) => item.example?.sv).slice(0, limit);
}

function renderPronunciation() {
  const items = filtered(pronunciationItems.length ? pronunciationItems : activeItems);
  const voice = swedishVoice();
  els.speechStatus.textContent = voice
    ? `Swedish voice ready: ${voice.name}. Select Listen to hear the correct accent.`
    : speechSupported()
      ? "No Swedish voice is ready yet. Install or enable a Swedish voice, then reload this page."
      : "Speech audio is not available in this browser. Use the reading aid below each word.";
  els.pronunciationList.innerHTML = items.map((item) => (
    `<article class="sound-card"><div class="sound-word">${escapeHTML(item.sv)}</div><div class="sound-meaning">${escapeHTML(item.en)}</div><div class="sound-guide"><strong>Reading aid:</strong> ${escapeHTML(item.pron || "No guide available")}</div><button class="listen-button" type="button" data-say="${escapeHTML(item.sv)}" ${voice ? "" : "disabled"}>${voice ? "Listen" : "Swedish voice unavailable"}</button></article>`
  )).join("");
}

function renderSentence() {
  const items = sampleItems();
  if (!items.length) return;
  sentencePractice.item = items[Math.floor(Math.random() * items.length)];
  sentencePractice.selected = [];
  renderSentenceBuilder();
}

function renderSentenceBuilder() {
  const item = sentencePractice.item;
  if (!item) return;
  const words = item.example.sv.split(" ");
  const available = [...words];
  sentencePractice.selected.forEach((word) => available.splice(available.indexOf(word), 1));
  els.sentenceCard.innerHTML = `<p class="sentence-label">Build the Swedish sentence</p><div class="sentence-translation"><strong>Meaning</strong> ${escapeHTML(item.example.en)}<br><span class="hindi"><strong>हिन्दी</strong> ${escapeHTML(item.example.hi)}</span></div><button class="listen-button" type="button" data-sentence-say="${escapeHTML(item.example.sv)}">Play Swedish sentence</button><div class="sentence-builder-result">${sentencePractice.selected.map(escapeHTML).join(" ") || "Choose the words below"}</div><div class="word-bank">${available.map((word) => `<button class="word-button" type="button" data-word="${escapeHTML(word)}">${escapeHTML(word)}</button>`).join("")}</div><button class="primary-button" id="checkSentence" type="button">Check sentence</button><p id="sentenceFeedback" class="quiz-feedback" aria-live="polite"></p>`;
}

function checkSentence() {
  const expected = sentencePractice.item.example.sv.split(" ").join(" ");
  const actual = sentencePractice.selected.join(" ");
  const feedback = document.getElementById("sentenceFeedback");
  feedback.textContent = actual === expected ? "Correct. You built the sentence." : `Not quite. Try again: ${expected}`;
}

function startPractice() {
  practice.correct = 0;
  practice.total = 0;
  renderQuizQuestion();
}

function renderQuizQuestion() {
  const pool = filtered().filter((item) => item.en);
  if (pool.length < 4) {
    els.quizCard.innerHTML = "<p>Add more vocabulary to this study set to start a test.</p>";
    return;
  }
  if (els.testMode.value === "grammar") {
    renderGrammarQuestion();
    return;
  }
  const question = pool[Math.floor(Math.random() * pool.length)];
  const mode = els.testMode.value;
  practice.question = question;
  if (mode === "spelling") {
    els.quizCard.innerHTML = `<p class="question-count">Question ${practice.total + 1}</p><div class="quiz-word">${escapeHTML(question.en)}</div><p class="quiz-prompt">Type the Swedish word or phrase.</p><input class="spelling-input" id="spellingAnswer" type="text" autocomplete="off" placeholder="Your Swedish answer"><button class="primary-button" id="checkSpelling" type="button">Check answer</button><p id="quizFeedback" class="quiz-feedback" aria-live="polite"></p>`;
    els.nextQuestion.textContent = "Next question";
    document.getElementById("checkSpelling").addEventListener("click", answerSpelling);
    return;
  }
  const options = [question, ...pool.filter((item) => item.id !== question.id).sort(() => Math.random() - .5).slice(0, 3)].sort(() => Math.random() - .5);
  const prompt = mode === "reverse" ? question.en : question.sv;
  const promptMarkup = mode === "listening" ? `<button class="quiz-listen" type="button" data-quiz-say="${escapeHTML(question.sv)}">Play Swedish audio</button>` : escapeHTML(prompt);
  const answerText = mode === "reverse" ? "sv" : "en";
  els.quizCard.innerHTML = `<p class="question-count">Question ${practice.total + 1}</p><div class="quiz-word">${promptMarkup}</div><div class="answer-grid">${options.map((item) => `<button class="answer-button" type="button" data-answer="${item.id}">${escapeHTML(item[answerText])}</button>`).join("")}</div><p id="quizFeedback" class="quiz-feedback" aria-live="polite"></p>`;
  els.nextQuestion.textContent = "Next question";
  els.quizCard.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", answerQuestion));
  els.quizCard.querySelectorAll("[data-quiz-say]").forEach((button) => button.addEventListener("click", () => speak(button.dataset.quizSay)));
}

function renderGrammarQuestion() {
  const examples = grammarGroups.flatMap((group) => group.lessons.flatMap((lesson) => (lesson.examples || []).map((example) => ({ ...example, lesson: lesson.title })))).filter((example) => example.sv.split(" ").length > 2);
  const example = examples[Math.floor(Math.random() * examples.length)];
  const words = example.sv.split(" ");
  const blankIndex = Math.min(words.length - 1, Math.max(1, Math.floor(words.length / 2)));
  const expectedWord = words[blankIndex];
  const distractors = [...new Set(examples.map((item) => item.sv.split(" ")[Math.min(blankIndex, item.sv.split(" ").length - 1)]).filter((word) => word && word !== expectedWord))].sort(() => Math.random() - .5).slice(0, 3);
  const options = [expectedWord, ...distractors].sort(() => Math.random() - .5);
  practice.question = { id: `grammar-${practice.total}-${expectedWord}`, sv: example.sv, en: example.en, forms: example.lesson, expectedWord };
  els.quizCard.innerHTML = `<p class="question-count">Question ${practice.total + 1}</p><div class="quiz-word">${escapeHTML(words.map((word, index) => index === blankIndex ? "_____" : word).join(" "))}</div><p class="quiz-prompt">Choose the word that completes the sentence.</p><div class="answer-grid">${options.map((word) => `<button class="answer-button" type="button" data-grammar-answer="${escapeHTML(word)}">${escapeHTML(word)}</button>`).join("")}</div><p id="quizFeedback" class="quiz-feedback" aria-live="polite"></p>`;
  els.nextQuestion.textContent = "Next question";
  els.quizCard.querySelectorAll("[data-grammar-answer]").forEach((button) => button.addEventListener("click", answerGrammarQuestion));
}

function answerGrammarQuestion(event) {
  els.quizCard.querySelectorAll("[data-grammar-answer]").forEach((button) => { button.disabled = true; });
  finishAnswer(event.currentTarget.dataset.grammarAnswer === practice.question.expectedWord, event.currentTarget);
}

function answerQuestion(event) {
  const buttons = els.quizCard.querySelectorAll("[data-answer]");
  buttons.forEach((button) => { button.disabled = true; });
  finishAnswer(Number(event.currentTarget.dataset.answer) === practice.question.id, event.currentTarget);
}

function answerSpelling() {
  const input = document.getElementById("spellingAnswer");
  const correct = norm(input.value.trim()) === norm(practice.question.sv);
  input.disabled = true;
  document.getElementById("checkSpelling").disabled = true;
  finishAnswer(correct, input);
}

function finishAnswer(correct, answerElement) {
  if (correct) practice.correct += 1;
  if (typeof practice.question.id === "number" && !correct && !progress.missed.includes(practice.question.id)) progress.missed.push(practice.question.id);
  if (typeof practice.question.id === "number" && correct) progress.missed = progress.missed.filter((id) => id !== practice.question.id);
  markReviewed();
  saveProgress();
  practice.total += 1;
  answerElement.classList.add(correct ? "correct" : "wrong");
  const feedback = document.getElementById("quizFeedback");
  feedback.textContent = correct ? "Correct. Nice work." : `Answer: ${practice.question.expectedWord || practice.question.sv}. ${practice.question.forms || "Try the example sentence."}`;
  els.scoreValue.textContent = `${practice.correct} / ${practice.total}`;
}

setup().catch((error) => {
  els.loading.hidden = true;
  els.empty.hidden = false;
  els.empty.textContent = "Could not load the vocabulary files. Please refresh the page.";
  console.error(error);
});
