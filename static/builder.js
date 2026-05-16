/**
 * Top-down character builder UI (loads /api/meta, previews via /api/preview).
 */
(function () {
  const DICE = ["Untrained", "d4", "d6", "d8", "d10", "d12"];
  const DICE_CORE = ["d4", "d6", "d8", "d10", "d12"];

  let meta = null;
  let previewTimer = null;
  /** null = no preview yet (show all edges); array = only these names in Human free dropdown */
  let lastHumanFreeEligible = null;

  function $(id) {
    return document.getElementById(id);
  }

  function hindrancePointsSelected() {
    const map = new Map((meta.hindrances || []).map((h) => [h.name, h.pts]));
    let pts = 0;
    document.querySelectorAll("#hindrance-checks input:checked").forEach((cb) => {
      pts += map.get(cb.value) || 0;
    });
    return pts;
  }

  function onHindranceChange() {
    const pts = hindrancePointsSelected();
    const el = $("hindrance-pts-label");
    el.textContent = `Selected hindrance points: ${pts} / 4`;
    el.style.color = pts > 4 ? "var(--bad)" : "var(--muted)";
    document.querySelectorAll("#hindrance-checks input").forEach((cb) => {
      if (!cb.checked) {
        const map = new Map((meta.hindrances || []).map((h) => [h.name, h.pts]));
        const tryPts = pts + (map.get(cb.value) || 0);
        cb.disabled = tryPts > 4;
      } else {
        cb.disabled = false;
      }
    });
    schedulePreview();
  }

  function buildHindrances() {
    const host = $("hindrance-checks");
    host.innerHTML = "";
    (meta.hindrances || []).forEach((h) => {
      const id = `hind-${h.name.replace(/[^a-zA-Z0-9]+/g, "-")}`;
      const lab = document.createElement("label");
      lab.className = "hindrance-entry";
      const inp = document.createElement("input");
      inp.type = "checkbox";
      inp.value = h.name;
      inp.id = id;
      inp.addEventListener("change", onHindranceChange);
      const text = document.createElement("div");
      text.className = "hindrance-text";
      const title = document.createElement("span");
      title.className = "hindrance-title";
      title.textContent = `${h.name} (${h.pts} pt)`;
      text.appendChild(title);
      const descText = (h.desc && String(h.desc).trim()) || "";
      if (descText) {
        const desc = document.createElement("span");
        desc.className = "hindrance-desc";
        desc.textContent = descText;
        text.appendChild(desc);
      }
      lab.appendChild(inp);
      lab.appendChild(text);
      host.appendChild(lab);
    });
    onHindranceChange();
  }

  function buildAttributes() {
    const host = $("attr-fields");
    host.innerHTML = "";
    (meta.attributes || []).forEach((attr) => {
      const wrap = document.createElement("div");
      const lab = document.createElement("label");
      lab.setAttribute("for", `attr-${attr}`);
      lab.textContent = attr;
      const sel = document.createElement("select");
      sel.id = `attr-${attr}`;
      DICE_CORE.forEach((d) => {
        const o = document.createElement("option");
        o.value = d;
        o.textContent = d;
        sel.appendChild(o);
      });
      sel.addEventListener("change", schedulePreview);
      wrap.appendChild(lab);
      wrap.appendChild(sel);
      host.appendChild(wrap);
    });
  }

  function buildSkills() {
    const tbody = document.querySelector("#skills-table tbody");
    tbody.innerHTML = "";
    const core = new Set(meta.core_skills || []);
    (meta.skill_order || []).forEach((skill) => {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td");
      td1.textContent = skill;
      const td2 = document.createElement("td");
      td2.textContent = meta.skill_attributes[skill] || "";
      td2.className = "muted";
      const td3 = document.createElement("td");
      const sel = document.createElement("select");
      sel.dataset.skill = skill;
      const opts = core.has(skill) ? DICE_CORE : DICE;
      opts.forEach((d) => {
        const o = document.createElement("option");
        o.value = d;
        o.textContent = d;
        sel.appendChild(o);
      });
      sel.value = core.has(skill) ? "d4" : "Untrained";
      sel.addEventListener("change", schedulePreview);
      td3.appendChild(sel);
      tr.appendChild(td1);
      tr.appendChild(td2);
      tr.appendChild(td3);
      tbody.appendChild(tr);
    });
  }

  function buildEdges() {
    const host = $("edge-checks");
    host.innerHTML = "";
    (meta.edges || []).forEach((e) => {
      const id = `edge-${e.name.replace(/[^a-zA-Z0-9]+/g, "-")}`;
      const lab = document.createElement("label");
      lab.className = "edge-entry";
      const inp = document.createElement("input");
      inp.type = "checkbox";
      inp.value = e.name;
      inp.id = id;
      inp.addEventListener("change", () => {
        const hf = $("human-free-edge").value;
        if (hf && inp.value === hf && !inp.checked) {
          $("human-free-edge").value = "";
        }
        schedulePreview();
      });
      const text = document.createElement("div");
      text.className = "edge-text";
      const title = document.createElement("span");
      title.className = "edge-title";
      title.textContent = e.name;
      text.appendChild(title);
      const reqText = (e.requirements && String(e.requirements).trim()) || "";
      if (reqText) {
        const req = document.createElement("span");
        req.className = "edge-req";
        req.textContent = `Requires: ${reqText}`;
        text.appendChild(req);
      }
      const descText = (e.desc && String(e.desc).trim()) || "";
      if (descText) {
        const desc = document.createElement("span");
        desc.className = "edge-desc";
        desc.textContent = descText;
        text.appendChild(desc);
      }
      lab.appendChild(inp);
      lab.appendChild(text);
      host.appendChild(lab);
    });
    const hfSel = $("human-free-edge");
    hfSel.addEventListener("change", onHumanFreeEdgeChange);
    hfSel.addEventListener("focus", onHumanFreeEdgeFocus);
    syncHumanFreeEdgeCheckbox();
  }

  function onHumanFreeEdgeFocus() {
    if ($("char-species").value !== "Human") return;
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = null;
    void runPreview();
  }

  function syncHumanFreeEdgeCheckbox() {
    if ($("char-species").value !== "Human") return;
    const v = $("human-free-edge").value;
    if (!v) return;
    document.querySelectorAll("#edge-checks input").forEach((inp) => {
      if (inp.value === v) inp.checked = true;
    });
  }

  function onHumanFreeEdgeChange() {
    syncHumanFreeEdgeCheckbox();
    schedulePreview();
  }

  function selectedEdges() {
    const edges = [];
    document.querySelectorAll("#edge-checks input:checked").forEach((cb) => edges.push(cb.value));
    return edges;
  }

  function refreshHumanFreeOptions() {
    const sel = $("human-free-edge");
    const wrap = $("human-free-wrap");
    const prev = sel.value;
    const human = $("char-species").value === "Human";
    sel.innerHTML = "";
    if (!human) {
      lastHumanFreeEligible = null;
      if (wrap) wrap.setAttribute("hidden", "");
      sel.disabled = true;
      const ph = document.createElement("option");
      ph.value = "";
      ph.textContent = "<choose>";
      sel.appendChild(ph);
      sel.value = "";
      return;
    }
    if (wrap) wrap.removeAttribute("hidden");
    sel.disabled = false;
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "<choose>";
    sel.appendChild(ph);
    const allNames = (meta.edges || []).map((e) => e.name);
    const names =
      lastHumanFreeEligible === null
        ? allNames
        : lastHumanFreeEligible.filter((n) => allNames.includes(n));
    names.forEach((name) => {
      const o = document.createElement("option");
      o.value = name;
      o.textContent = name;
      sel.appendChild(o);
    });
    if (names.includes(prev)) {
      sel.value = prev;
    } else {
      sel.value = "";
    }
    syncHumanFreeEdgeCheckbox();
  }

  function buildQtyRow(container, name, cost, meta2) {
    // meta2: optional { damage, range } for weapons
    const row = document.createElement("div");
    row.className = "qty-row";
    row.dataset.item = name;

    const minus = document.createElement("button");
    minus.type = "button";
    minus.className = "qty-btn";
    minus.textContent = "−";

    const countEl = document.createElement("span");
    countEl.className = "qty-count";
    countEl.textContent = "0";

    const plus = document.createElement("button");
    plus.type = "button";
    plus.className = "qty-btn";
    plus.textContent = "+";

    const lbl = document.createElement("span");
    lbl.className = "qty-label";
    lbl.textContent = name;

    const sub = document.createElement("span");
    sub.className = "qty-sub";
    const parts = [`${cost} cr`];
    if (meta2 && meta2.damage) parts.push(meta2.damage);
    if (meta2 && meta2.range)  parts.push(`Range ${meta2.range}`);
    sub.textContent = parts.join("  ·  ");

    minus.addEventListener("click", () => {
      const n = parseInt(countEl.textContent) || 0;
      if (n > 0) {
        countEl.textContent = n - 1;
        countEl.classList.toggle("active", n - 1 > 0);
        schedulePreview();
      }
    });

    plus.addEventListener("click", () => {
      const n = parseInt(countEl.textContent) || 0;
      countEl.textContent = n + 1;
      countEl.classList.add("active");
      schedulePreview();
    });

    row.appendChild(minus);
    row.appendChild(countEl);
    row.appendChild(plus);
    const textWrap = document.createElement("span");
    textWrap.style.cssText = "display:flex;flex-direction:column;gap:0.05rem;";
    textWrap.appendChild(lbl);
    textWrap.appendChild(sub);
    row.appendChild(textWrap);
    container.appendChild(row);
  }

  function buildWeaponsGear() {
    const wh = $("weapon-checks");
    wh.innerHTML = "";
    (meta.weapons || []).forEach((w) => buildQtyRow(wh, w.name, w.cost, { damage: w.damage, range: w.range }));

    const arm = $("armor-select");
    arm.innerHTML = "";
    const noneOpt = document.createElement("option");
    noneOpt.value = "";
    noneOpt.textContent = "(none)";
    arm.appendChild(noneOpt);
    (meta.armor || []).forEach((a) => {
      const o = document.createElement("option");
      o.value = a.name;
      o.textContent = `${a.name} (${a.cost} cr)`;
      arm.appendChild(o);
    });
    arm.value = "";
    arm.addEventListener("change", schedulePreview);

    const gh = $("gear-checks");
    gh.innerHTML = "";
    (meta.gear || []).forEach((g) => buildQtyRow(gh, g.name, g.cost));
  }

  function buildSpeciesSelect() {
    const sel = $("char-species");
    sel.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "<choose>";
    sel.appendChild(ph);
    (meta.species || []).forEach((s) => {
      const o = document.createElement("option");
      o.value = s.name;
      o.textContent = s.name;
      sel.appendChild(o);
    });
    sel.value = "";
    sel.addEventListener("change", () => {
      updateSpeciesBlurb();
      schedulePreview();
    });
    updateSpeciesBlurb();
  }

  function buildCareerSelect() {
    const sel = $("char-career");
    sel.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "<choose>";
    sel.appendChild(ph);
    (meta.careers || []).forEach((c) => {
      const o = document.createElement("option");
      o.value = c.name;
      o.textContent = c.name;
      sel.appendChild(o);
    });
    sel.value = "";
    sel.addEventListener("change", () => {
      updateCareerBlurb();
      // Auto-populate skills with career defaults; user can edit freely after
      void applyCareerSkills(true);
    });
    updateCareerBlurb();
  }

  function updateCareerBlurb() {
    const name = $("char-career").value;
    const cr = (meta.careers || []).find((c) => c.name === name);
    const el = $("career-blurb");
    if (!cr) {
      el.textContent = "";
      return;
    }
    const parts = [];
    const benefits = Array.isArray(cr.benefits) ? cr.benefits : [];
    benefits.forEach((b) => {
      if (!b || typeof b !== "object") return;
      const t = (b.title && String(b.title).trim()) || "";
      const ty = (b.type && String(b.type).trim()) || "";
      const eff = (b.effect && String(b.effect).trim()) || "";
      const tag = ty ? ` [${ty}]` : "";
      if (t && eff) parts.push(`• ${t}${tag}: ${eff}`);
      else if (t) parts.push(`• ${t}${tag}`);
      else if (eff) parts.push(`• ${eff}`);
    });
    el.textContent = parts.join("\n\n");
  }

  function updateSpeciesBlurb() {
    const name = $("char-species").value;
    const sp = (meta.species || []).find((s) => s.name === name);
    const el = $("species-blurb");
    if (!sp) {
      el.textContent = "";
    } else {
      el.textContent = [sp.abilities, sp.notes].filter(Boolean).join("\n\n");
    }
    refreshHumanFreeOptions();
  }

  function collectPayload() {
    const attributes = {};
    (meta.attributes || []).forEach((attr) => {
      const sel = $(`attr-${attr}`);
      if (sel) attributes[attr] = sel.value;
    });

    const skills = {};
    document.querySelectorAll("#skills-table select[data-skill]").forEach((sel) => {
      skills[sel.dataset.skill] = sel.value;
    });

    const hindrances = [];
    document.querySelectorAll("#hindrance-checks input:checked").forEach((cb) => hindrances.push(cb.value));

    let edges = selectedEdges();
    const isHuman = $("char-species").value === "Human";
    const humanFree = $("human-free-edge").value;
    let human_free_edges_used = [];
    if (isHuman && humanFree) {
      human_free_edges_used = [humanFree];
      if (!edges.includes(humanFree)) {
        edges = [...edges, humanFree];
      }
    }

    const weapons = [];
    document.querySelectorAll("#weapon-checks .qty-row").forEach((row) => {
      const qty = parseInt(row.querySelector(".qty-count").textContent) || 0;
      for (let i = 0; i < qty; i++) weapons.push(row.dataset.item);
    });

    const gear = [];
    document.querySelectorAll("#gear-checks .qty-row").forEach((row) => {
      const qty = parseInt(row.querySelector(".qty-count").textContent) || 0;
      for (let i = 0; i < qty; i++) gear.push(row.dataset.item);
    });

    return {
      name: ($("char-name").value || "").trim(),
      species: $("char-species").value,
      career: $("char-career").value,
      hindrances,
      attributes,
      skills,
      edges,
      human_free_edges_used,
      weapons,
      armor: $("armor-select").value,
      gear,
    };
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
  }

  function tRow(label, valueHtml, valueNeg) {
    const neg = valueNeg ? " neg" : "";
    return `<div class="t-row"><span class="t-label">${esc(label)}</span><span class="t-val${neg}">${valueHtml}</span></div>`;
  }

  function section(title) {
    return `<div class="t-section">${esc(title)}</div>`;
  }

  function totalsExplain(text) {
    return `<div class="t-row t-explain"><span class="t-explain-text">${esc(text)}</span></div>`;
  }

  function syncFormFromCharacter(c) {
    if (!c || !meta) return;
    const careerSel = $("char-career");
    if (careerSel && Object.prototype.hasOwnProperty.call(c, "career")) {
      const cr = String(c.career || "");
      if (cr && [...careerSel.options].some((o) => o.value === cr)) careerSel.value = cr;
    }
    updateCareerBlurb();
    const attrs = c.attributes || {};
    (meta.attributes || []).forEach((attr) => {
      const sel = $(`attr-${attr}`);
      if (sel && attrs[attr]) sel.value = attrs[attr];
    });
    const skills = c.skills || {};
    document.querySelectorAll("#skills-table select[data-skill]").forEach((sel) => {
      const sk = sel.dataset.skill;
      if (Object.prototype.hasOwnProperty.call(skills, sk)) sel.value = skills[sk];
    });
    const armSel = $("armor-select");
    if (armSel && Object.prototype.hasOwnProperty.call(c, "armor")) {
      const ar = String(c.armor ?? "");
      if (ar && [...armSel.options].some((o) => o.value === ar)) armSel.value = ar;
      else armSel.value = "";
    }

    // Sync weapon quantities
    if (Array.isArray(c.weapons)) {
      const weapCounts = {};
      c.weapons.forEach((w) => { weapCounts[w] = (weapCounts[w] || 0) + 1; });
      document.querySelectorAll("#weapon-checks .qty-row").forEach((row) => {
        const qty = weapCounts[row.dataset.item] || 0;
        const countEl = row.querySelector(".qty-count");
        if (countEl) { countEl.textContent = qty; countEl.classList.toggle("active", qty > 0); }
      });
    }

    // Sync gear quantities
    if (Array.isArray(c.gear)) {
      const gearCounts = {};
      c.gear.forEach((g) => { gearCounts[g] = (gearCounts[g] || 0) + 1; });
      document.querySelectorAll("#gear-checks .qty-row").forEach((row) => {
        const qty = gearCounts[row.dataset.item] || 0;
        const countEl = row.querySelector(".qty-count");
        if (countEl) { countEl.textContent = qty; countEl.classList.toggle("active", qty > 0); }
      });
    }
  }

  function renderLiveTotals(t) {
    const host = $("live-totals");
    if (!t) {
      host.innerHTML = "";
      return;
    }
    const h = t.hindrance_points_from_hindrances;
    const hMax = t.hindrance_points_max;
    const gift = Number(t.species_attribute_steps_gift) || 0;
    const billable =
      t.attribute_steps_billable != null ? t.attribute_steps_billable : t.attribute_die_steps;
    const parts = [
      section("Hindrances"),
      tRow(
        "Hindrance points (from choices)",
        `${esc(h)} / ${esc(hMax)}`,
        h > hMax
      ),
      section("Attributes"),
      tRow("Die steps above d4 (all attrs)", esc(t.attribute_die_steps), false),
    ];
    if (gift > 0) {
      parts.push(
        tRow(
          "Species / racial attribute steps (not counted vs. 5 free)",
          esc(gift),
          false
        )
      );
    }
    parts.push(
      tRow("Steps counted vs. creation budget", esc(billable), false),
      tRow("Free steps from character creation", esc(t.attribute_free_steps), false),
      tRow("Hindrance pts spent on extra steps", esc(t.hindrance_spent_on_attributes), t.hindrance_spent_on_attributes > h),
      tRow("Hindrance pool after attributes", esc(t.hindrance_pool_after_attributes), t.hindrance_pool_after_attributes < 0),
      section("Skills"),
      tRow(
        "Skill budget (15 + unspent hindrance)",
        esc(t.skill_points_budget),
        t.skill_points_budget < 0
      ),
      tRow("Skill points spent", esc(t.skill_points_spent), false),
      tRow("Skill points remaining", esc(t.skill_points_remaining), t.skill_points_remaining < 0),
      tRow(
        "Spent above 15 (drawn from hindrance pool)",
        esc(t.hindrance_used_by_skills_past_15),
        false
      ),
      tRow("Hindrance left for Edges", esc(t.hindrance_pool_after_skills), t.hindrance_pool_after_skills < 0),
      section("Edges"),
      tRow("Edges selected", esc(t.edges_selected), false),
      tRow("Edges paid with hindrance (not free)", esc(t.edges_paid_with_hindrance), false),
      tRow("Hindrance pts spent on edges", esc(t.hindrance_spent_on_edges), t.hindrance_spent_on_edges > t.hindrance_pool_after_skills),
      tRow("Hindrance pool after edges", esc(t.hindrance_pool_after_edges), t.hindrance_pool_after_edges < 0),
      section("Species / credits"),
      tRow("Human free edge applied", t.human_species ? esc(`${t.human_free_edges_applied} / ${t.human_free_edge_slots}`) : "—", false),
      tRow("Starting credits", esc(t.starting_credits), false),
      tRow("Credits remaining", esc(t.credits_remaining), t.credits_remaining < 0),
      section("Derived"),
      tRow("Toughness", esc(t.toughness), false),
      tRow("Parry", esc(t.parry), false)
    );
    host.innerHTML = parts.join("");
  }

  function updateLiveValidation(errors, ok) {
    const el = $("live-validation");
    if (!errors || errors.length === 0) {
      el.textContent = ok ? "Build passes validation." : "Waiting for preview…";
      el.className = ok ? "ok" : "";
      return;
    }
    el.textContent = errors.join("\n");
    el.className = "bad";
  }

  async function runPreview() {
    const valEl = $("live-validation");
    valEl.textContent = "Updating…";
    valEl.className = "";
    try {
      const res = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectPayload()),
      });
      const data = await res.json();
      $("sheet").textContent = data.sheet_text || "";
      renderLiveTotals(data.totals);
      if (data.character) syncFormFromCharacter(data.character);
      updateLiveValidation(data.errors || [], data.ok);
      if (Array.isArray(data.human_free_eligible_edges)) {
        lastHumanFreeEligible = data.human_free_eligible_edges;
      }
      if ($("char-species").value === "Human") {
        refreshHumanFreeOptions();
      }
    } catch (e) {
      renderLiveTotals(null);
      updateLiveValidation([String(e)], false);
    }
  }

  function schedulePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(runPreview, 380);
  }

  async function fetchSheet() {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: collectPayload() }),
    });
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail;
      const msg =
        d && typeof d === "object" && Array.isArray(d.errors)
          ? d.errors.join("\n")
          : typeof d === "string"
            ? d
            : JSON.stringify(d || data);
      updateLiveValidation([msg], false);
      $("status").textContent = "Validation failed — fix errors before exporting.";
      return null;
    }
    updateLiveValidation([], true);
    return data;
  }

  async function openSheet() {
    $("status").textContent = "";
    const data = await fetchSheet();
    if (!data) return;
    const blob = new Blob([data.sheet_html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    $("status").textContent = "Sheet opened in new tab.";
  }

  async function downloadJSON() {
    $("status").textContent = "";
    const data = await fetchSheet();
    if (!data) return;
    const blob = new Blob([JSON.stringify(data.character, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const name = (data.character.name || "character").replace(/[\\/:*?"<>|]/g, "_");
    a.href = url;
    a.download = `${name}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    $("status").textContent = "JSON downloaded.";
  }

  /**
   * Fetch career skill suggestion from the server and apply it to the skill table.
   * @param {boolean} silent - when true, suppress the status note (used for auto-apply on career change)
   */
  async function applyCareerSkills(silent) {
    const career = $("char-career").value;
    const note = $("suggest-skills-note");

    if (!career) {
      if (!silent) {
        note.textContent = "Choose a career first.";
        note.style.color = "var(--warn)";
      }
      return;
    }

    const attributes = {};
    (meta.attributes || []).forEach((attr) => {
      const sel = $(`attr-${attr}`);
      if (sel) attributes[attr] = sel.value;
    });

    if (!silent) {
      note.textContent = "Calculating…";
      note.style.color = "var(--muted)";
    }

    try {
      const res = await fetch("/api/suggest-skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          career,
          species: $("char-species").value,
          attributes,
        }),
      });

      if (!res.ok) {
        if (!silent) {
          const err = await res.json().catch(() => ({}));
          note.textContent =
            err.detail && typeof err.detail === "string"
              ? err.detail
              : "No suggestion available for this career.";
          note.style.color = "var(--warn)";
        }
        return;
      }

      const data = await res.json();
      const suggested = data.skills || {};
      const core = new Set(meta.core_skills || []);

      // Apply suggested values; skills remain freely editable after this
      document.querySelectorAll("#skills-table select[data-skill]").forEach((sel) => {
        const sk = sel.dataset.skill;
        const val = Object.prototype.hasOwnProperty.call(suggested, sk)
          ? suggested[sk]
          : core.has(sk) ? "d4" : "Untrained";
        if ([...sel.options].some((o) => o.value === val)) {
          sel.value = val;
        }
      });

      if (!silent) {
        note.textContent = `Reset to ${career} defaults.`;
        note.style.color = "var(--good)";
      } else {
        note.textContent = "";
      }

      schedulePreview();
    } catch (e) {
      if (!silent) {
        note.textContent = String(e);
        note.style.color = "var(--bad)";
      }
    }
  }

  async function init() {
    const res = await fetch("/api/meta");
    meta = await res.json();

    buildSpeciesSelect();
    buildCareerSelect();
    $("char-name").addEventListener("input", schedulePreview);

    buildHindrances();
    buildAttributes();
    buildSkills();
    buildEdges();
    buildWeaponsGear();

    $("btn-suggest-skills").addEventListener("click", () => applyCareerSkills(false));
    $("btn-open-sheet").addEventListener("click", openSheet);
    $("btn-download-json").addEventListener("click", downloadJSON);

    await runPreview();
  }

  init().catch((e) => {
    renderLiveTotals(null);
    updateLiveValidation([`Failed to load: ${e}`], false);
  });
})();
