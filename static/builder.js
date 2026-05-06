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

  function buildWeaponsGear() {
    const wh = $("weapon-checks");
    wh.innerHTML = "";
    (meta.weapons || []).forEach((w) => {
      const lab = document.createElement("label");
      const inp = document.createElement("input");
      inp.type = "checkbox";
      inp.value = w.name;
      inp.addEventListener("change", schedulePreview);
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(` ${w.name} (${w.cost} cr)`));
      wh.appendChild(lab);
    });

    const arm = $("armor-select");
    arm.innerHTML = "";
    (meta.armor || []).forEach((a) => {
      const o = document.createElement("option");
      o.value = a.name;
      o.textContent = `${a.name} (${a.cost} cr)`;
      arm.appendChild(o);
    });
    arm.value = "No Armor";
    arm.addEventListener("change", schedulePreview);

    const gh = $("gear-checks");
    gh.innerHTML = "";
    (meta.gear || []).forEach((g) => {
      const lab = document.createElement("label");
      const inp = document.createElement("input");
      inp.type = "checkbox";
      inp.value = g.name;
      inp.addEventListener("change", schedulePreview);
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(` ${g.name} (${g.cost} cr)`));
      gh.appendChild(lab);
    });
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
      schedulePreview();
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
    document.querySelectorAll("#weapon-checks input:checked").forEach((cb) => weapons.push(cb.value));

    const gear = [];
    document.querySelectorAll("#gear-checks input:checked").forEach((cb) => gear.push(cb.value));

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
        "Skill budget (15 + hindrance after attributes)",
        esc(t.skill_points_budget),
        t.skill_points_budget < 0
      ),
      tRow("Total skill purchase cost", esc(t.skill_points_spent), false),
      tRow("Skill budget remaining", esc(t.skill_points_remaining), t.skill_points_remaining < 0),
      tRow(
        "Skill cost past the free 15 (1:1 from hindrance pool)",
        esc(t.hindrance_used_by_skills_past_15),
        false
      ),
      tRow("Hindrance left for Edges (after skills)", esc(t.hindrance_pool_after_skills), t.hindrance_pool_after_skills < 0),
      totalsExplain(
        "One wallet: “Skill budget remaining” is (15 + hindrance after attributes) minus total skill cost. " +
          "“Skill cost past the free 15” is only the slice of that same cost above 15; it reserves hindrance for the math on Edges. " +
          "So you can still see budget headroom while hindrance-for-Edges goes down—same purchase, two labels."
      ),
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

  function setSaveStatusLinks(items) {
    const el = $("status");
    el.replaceChildren();
    if (!items || !items.length) return;
    el.appendChild(document.createTextNode("Saved: "));
    items.forEach((item, i) => {
      if (i > 0) el.appendChild(document.createTextNode("; "));
      const a = document.createElement("a");
      a.href = item.href || "#";
      a.textContent = item.path || item.filename || "file";
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      el.appendChild(a);
    });
  }

  async function saveFiles() {
    $("status").replaceChildren();
    try {
      const res = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character: collectPayload(),
          save_json: $("save-json").checked,
          save_html: $("save-html").checked,
          save_txt: $("save-txt").checked,
        }),
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
        $("status").textContent = "Save failed.";
        return;
      }
      updateLiveValidation([], true);
      if (Array.isArray(data.saved_items) && data.saved_items.length) {
        setSaveStatusLinks(data.saved_items);
      } else {
        $("status").textContent = "Saved: " + (data.saved || []).join("; ");
      }
    } catch (e) {
      updateLiveValidation([String(e)], false);
      $("status").textContent = "Save failed.";
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

    $("btn-save").addEventListener("click", saveFiles);

    await runPreview();
  }

  init().catch((e) => {
    renderLiveTotals(null);
    updateLiveValidation([`Failed to load: ${e}`], false);
  });
})();
