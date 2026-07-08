// UI wiring for the static generator page. No dependencies; createModel
// comes from model.js (loaded as a preceding <script> tag).

async function main() {
  const [weights, vocabPayload, mapData] = await Promise.all([
    fetch("weights_flat.json").then((r) => r.json()),
    fetch("vocab.json").then((r) => r.json()),
    fetch("map_paths.json").then((r) => r.json()),
  ]);

  const model = createModel(weights, vocabPayload.vocab, vocabPayload.rev_vocab);

  const nameToCode = {};
  const codeToName = {};
  for (const s of mapData.states) {
    if (s.selectable) {
      nameToCode[s.name] = s.code;
      codeToName[s.code] = s.name;
    }
  }

  // --- Shared selection state: map clicks and the <select> both read/write
  // this array of state names, kept in sync the same way app_marimo.py's
  // get_selected/set_selected pair does (app_marimo.py:210-332), just as
  // plain functions instead of reactive cells.
  let selected = [];

  const svg = document.getElementById("map");
  svg.setAttribute("viewBox", `0 0 ${mapData.size.w} ${mapData.size.h}`);
  const pathEls = {};

  function fillFor(state, isSelected) {
    if (!state.selectable) return "#e5e5e5";
    return isSelected ? "#ffc53a" : "#94a3b8";
  }

  for (const state of mapData.states) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", state.path);
    p.setAttribute("fill", fillFor(state, false));
    if (state.selectable) {
      p.classList.add("selectable");
      p.addEventListener("click", () => {
        toggleSelected(state.name);
      });
    }
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = state.name;
    p.appendChild(title);
    svg.appendChild(p);
    pathEls[state.name] = { el: p, state };
  }

  const selectEl = document.getElementById("states-select");
  for (const name of Object.keys(nameToCode).sort()) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    selectEl.appendChild(opt);
  }

  function syncUI() {
    for (const name of Object.keys(pathEls)) {
      const { el, state } = pathEls[name];
      el.setAttribute("fill", fillFor(state, selected.includes(name)));
    }
    for (const opt of selectEl.options) {
      opt.selected = selected.includes(opt.value);
    }
  }

  function toggleSelected(name) {
    if (selected.includes(name)) {
      selected = selected.filter((n) => n !== name);
    } else {
      selected = [...selected, name].sort();
    }
    syncUI();
  }

  selectEl.addEventListener("change", () => {
    selected = Array.from(selectEl.selectedOptions).map((o) => o.value).sort();
    syncUI();
  });

  const startTextEl = document.getElementById("start-text");
  const countEl = document.getElementById("count");
  const resultsEl = document.getElementById("results");

  document.getElementById("generate-btn").addEventListener("click", () => {
    const startText = startTextEl.value;
    const count = Math.max(1, Math.min(25, parseInt(countEl.value, 10) || 1));
    const stateCodes = selected.map((n) => nameToCode[n]).filter(Boolean);

    const results = model.generate(startText, count, stateCodes);
    const items = results
      .map((r) => {
        const stateName = codeToName[r.code];
        return stateName ? `<li><strong>${r.name}</strong>, ${stateName}</li>` : `<li><strong>${r.name}</strong></li>`;
      })
      .join("");
    resultsEl.innerHTML = `<p><strong>Generated names</strong></p><ul>${items}</ul>`;
  });
}

main();
