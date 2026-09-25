const state = {
  category: "",
  level: "all",
  set: "all",
  type: "all",
  query: "",
  view: "cards",
  theme: localStorage.getItem("theme") || "light",
};

const cache = new Map();
let manifest = null;
let activeItems = [];

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
  empty: document.getElementById("emptyState"),
  loading: document.getElementById("loadingState"),
  cardsView: document.getElementById("cardsView"),
  tableView: document.getElementById("tableView"),
  notes: document.getElementById("grammarNotes"),
  themeToggle: document.getElementById("themeToggle"),
};

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
  manifest = await fetchJSON("data/manifest.json");
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

  els.notes.innerHTML = manifest.notes.map((note) => (
    `<article class="note"><h3>${escapeHTML(note.title)}</h3><p>${escapeHTML(note.body)}</p></article>`
  )).join("");

  els.category.value = state.category;
  bindEvents();
  await loadAndRender();
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
    render();
  });

  els.chips.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;
    state.category = button.dataset.category;
    els.category.value = state.category;
    syncChips();
    await loadAndRender();
  });

  els.cardsView.addEventListener("click", () => setView("cards"));
  els.tableView.addEventListener("click", () => setView("table"));
  els.themeToggle.addEventListener("click", () => {
    applyTheme(state.theme === "dark" ? "light" : "dark");
  });
}

async function fetchJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
}

async function loadCategory(slug) {
  if (!cache.has(slug)) {
    const chunk = await fetchJSON(`data/chunks/${slug}.json`);
    cache.set(slug, chunk.items);
  }
  return cache.get(slug);
}

async function loadActiveItems() {
  if (state.category === "all" || state.set === "quick") {
    const groups = await Promise.all(manifest.chapters.map((chapter) => loadCategory(chapter.slug)));
    return groups.flat();
  }
  return loadCategory(state.category);
}

async function loadAndRender() {
  els.loading.hidden = false;
  els.empty.hidden = true;
  els.cards.hidden = true;
  els.tableWrap.hidden = true;
  try {
    activeItems = await loadActiveItems();
    syncChips();
    render();
  } finally {
    els.loading.hidden = true;
    applyViewVisibility();
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

function filtered() {
  const quickSet = new Set(manifest.quickIds);
  const query = norm(state.query.trim());
  return activeItems.filter((item) => {
    if (state.level !== "all" && item.level !== state.level) return false;
    if (state.type !== "all" && item.kind !== state.type) return false;
    if (state.set === "quick" && !quickSet.has(item.id)) return false;
    if (query) {
      const haystack = norm([
        item.sv,
        item.en,
        item.hi,
        item.pron,
        item.forms,
        item.categoryLabel,
        item.example?.sv,
        item.example?.en,
        item.example?.hi,
      ].join(" "));
      if (!haystack.includes(query)) return false;
    }
    return true;
  });
}

function render() {
  const rows = filtered();
  els.visible.textContent = rows.length.toLocaleString();
  els.empty.hidden = rows.length !== 0;
  if (state.view === "cards") renderCards(rows);
  if (state.view === "table") renderTable(rows);
}

function renderCards(rows) {
  els.cards.innerHTML = rows.map((item) => (
    `<article class="vocab-card">
      <div class="card-meta"><span>${escapeHTML(item.categoryLabel)}</span><span class="badge">${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</span></div>
      <div class="swedish">${escapeHTML(item.sv)}</div>
      <div class="meaning">
        <div><strong>English:</strong> ${escapeHTML(item.en)}</div>
        <div class="hindi"><strong>हिन्दी:</strong> ${escapeHTML(item.hi)}</div>
      </div>
      <div class="forms">${escapeHTML(item.forms || "")}</div>
      ${item.pron ? `<div class="pron">Say it: ${escapeHTML(item.pron)}</div>` : ""}
      <div class="example">
        <p><span>SV</span> ${escapeHTML(item.example.sv)}</p>
        <p><span>EN</span> ${escapeHTML(item.example.en)}</p>
        <p class="hindi"><span>HI</span> ${escapeHTML(item.example.hi)}</p>
      </div>
    </article>`
  )).join("");
}

function renderTable(rows) {
  els.tableBody.innerHTML = rows.map((item) => (
    `<tr>
      <td>${escapeHTML(item.sv)}<br><small>${escapeHTML(item.categoryLabel)} · ${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</small></td>
      <td>${escapeHTML(item.en)}</td>
      <td class="hindi">${escapeHTML(item.hi)}</td>
      <td>${escapeHTML(item.forms || "")}${item.pron ? `<br><small>Say it: ${escapeHTML(item.pron)}</small>` : ""}</td>
      <td><strong>SV</strong> ${escapeHTML(item.example.sv)}<br><strong>EN</strong> ${escapeHTML(item.example.en)}<br><span class="hindi"><strong>HI</strong> ${escapeHTML(item.example.hi)}</span></td>
    </tr>`
  )).join("");
}

setup().catch((error) => {
  els.loading.hidden = true;
  els.empty.hidden = false;
  els.empty.textContent = "Could not load the vocabulary files. Please refresh the page.";
  console.error(error);
});
