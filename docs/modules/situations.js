export function createSituationsController({ select, content, speak, escapeHTML }) {
  let bank = [];
  function render() {
    if (!select || !content) return;
    const scenario = bank.find((item) => item.id === select.value) || bank[0];
    if (!scenario) {
      content.innerHTML = "";
      return;
    }

    const dialogue = scenario.dialogue.map((line) => (
      `<div class="situation-line"><button class="play-button" type="button" data-situation-say="${escapeHTML(line.sv)}" aria-label="Play the Swedish line ${escapeHTML(line.sv)}">Play</button><div><strong>${escapeHTML(line.sv)}</strong><span>${escapeHTML(line.en)}</span><small>${escapeHTML(line.hi)}</small></div></div>`
    )).join("");
    const options = scenario.options.map((option) => (
      `<button class="answer-button" type="button" data-situation-answer="${escapeHTML(option)}">${escapeHTML(option)}</button>`
    )).join("");

    content.innerHTML = `
      <div class="situation-layout-inner">
        <div class="situation-card">
          <p class="situation-label">Scenario goal</p>
          <h3>${escapeHTML(scenario.title)}</h3>
          <p class="situation-goal">${escapeHTML(scenario.goal)}</p>
          <div class="situation-vocab"><strong>Useful phrases</strong><ul>${scenario.vocab.map((phrase) => `<li>${escapeHTML(phrase)}</li>`).join("")}</ul></div>
          <div class="situation-dialogue">${dialogue}</div>
        </div>
        <div class="situation-card">
          <p class="situation-label">Quick check</p>
          <p class="quiz-prompt">${escapeHTML(scenario.prompt)}</p>
          <div class="answer-grid">${options}</div>
          <p id="situationFeedback" class="quiz-feedback" aria-live="polite"></p>
        </div>
      </div>
    `;

    content.querySelectorAll("[data-situation-say]").forEach((button) => {
      button.addEventListener("click", () => speak(button.dataset.situationSay));
    });
    content.querySelectorAll("[data-situation-answer]").forEach((button) => {
      button.addEventListener("click", () => {
        const correct = button.dataset.situationAnswer === scenario.answer;
        content.querySelectorAll("[data-situation-answer]").forEach((option) => { option.disabled = true; });
        const feedback = content.querySelector("#situationFeedback");
        feedback.textContent = correct ? `Correct. ${scenario.answer}` : `Best answer: ${scenario.answer}`;
        button.classList.add(correct ? "correct" : "wrong");
      });
    });
  }

  async function load() {
    if (!select || bank.length) return;
    const response = await fetch("/api/situations");
    if (!response.ok) throw new Error("Could not load situation practice.");
    bank = await response.json();
    select.innerHTML = bank.map((scenario) => (
      `<option value="${escapeHTML(scenario.id)}">${escapeHTML(scenario.title)}</option>`
    )).join("");
    if (bank[0]) select.value = bank[0].id;
    select.addEventListener("change", render);
    render();
  }

  return { load, render };
}