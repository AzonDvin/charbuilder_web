"""
Generate docs/character_manual.html from data/*.json (character builder reference).
Run from repo root: python scripts/generate_character_manual.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "character_manual.html"


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def load(name: str) -> dict | list:
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def table_head(cols: list[str]) -> str:
    return (
        "<thead><tr>"
        + "".join(f"<th>{esc(c)}</th>" for c in cols)
        + "</tr></thead>"
    )


def main() -> None:
    species = load("species.json")
    careers = load("careers.json")
    hindrances = load("hindrances.json")
    attrs_data = load("attributes.json")
    edges = load("edges.json")
    gear = load("gear.json")
    attachments = load("attachments.json")

    attr_list = attrs_data.get("attributes", [])
    skill_attrs = attrs_data.get("skill_attributes", {})
    core_skills = set(attrs_data.get("core_skills", []))

    weapons = [(k, v) for k, v in gear.items() if v.get("category") == "weapon"]
    armor = [(k, v) for k, v in gear.items() if v.get("category") == "armor"]
    ggear = [(k, v) for k, v in gear.items() if v.get("category") == "gear"]

    def sort_gear(items):
        return sorted(
            items,
            key=lambda x: (x[1].get("cost", 0), x[0].lower()),
        )

    weapons = sort_gear(weapons)
    armor = sort_gear(armor)
    ggear = sort_gear(ggear)

    attach_rows = sorted(
        attachments.items(),
        key=lambda x: (
            x[1].get("kind", ""),
            x[1].get("cost", 0),
            x[1].get("hardPointCost", 0),
            x[0].lower(),
        ),
    )

    hind_rows = sorted(
        hindrances.items(),
        key=lambda x: (-x[1].get("pts", 0), x[0].lower()),
    )

    edge_rows = sorted(edges.items(), key=lambda x: x[0].lower())

    skill_rows = sorted(skill_attrs.items(), key=lambda x: x[0].lower())

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append(
        "<title>Character Builder Reference Manual</title>"
    )
    parts.append(
        """<style>
:root {
  --bg: #f4f6fb;
  --text: #1a1d26;
  --muted: #5c6578;
  --border: #c9ced9;
  --head: #1a3a6b;
  --accent: #1a3a6b;
  --accent-light: #e8edf8;
}
* { box-sizing: border-box; }
body { font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.5; color: var(--text); background: var(--bg); margin: 0; padding: 1.5rem 2rem 3rem; max-width: 1100px; margin-left: auto; margin-right: auto; }
h1 { color: var(--head); font-size: 1.8rem; margin-top: 0; border-bottom: 3px solid var(--accent); padding-bottom: 0.4rem; }
h2 { color: var(--head); font-size: 1.25rem; margin-top: 2.5rem; padding: 0.3rem 0.7rem; background: var(--accent); color: #fff; border-radius: 3px; }
h3 { color: var(--head); font-size: 1.05rem; margin-top: 1.5rem; border-left: 4px solid var(--accent); padding-left: 0.5rem; }
p.lead { color: var(--muted); font-size: 1.05rem; }
.meta { font-size: 0.88rem; color: var(--muted); margin-bottom: 1.5rem; background: var(--accent-light); padding: 0.5rem 0.75rem; border-radius: 4px; border-left: 3px solid var(--accent); }
table { width: 100%; border-collapse: collapse; margin: 1rem 0 1.5rem; font-size: 0.91rem; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.07); border-radius: 4px; overflow: hidden; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.7rem; text-align: left; vertical-align: top; }
th { background: var(--accent); color: #fff; font-weight: 600; }
tr:nth-child(even) td { background: #f8fafd; }
tr:hover td { background: var(--accent-light); }
.career-desc { color: var(--muted); margin: 0.25rem 0 0.75rem; font-style: italic; }
ul.steps { margin: 0.5rem 0 1rem 1.2rem; }
ul.steps li { margin: 0.45rem 0; }
a.nav { color: var(--accent); font-weight: 500; text-decoration: none; }
a.nav:hover { text-decoration: underline; }
.nav-bar { display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem; background: var(--accent); padding: 0.6rem 0.9rem; border-radius: 4px; margin: 1.2rem 0; }
.nav-bar a { color: #fff; font-size: 0.88rem; text-decoration: none; }
.nav-bar a:hover { text-decoration: underline; }
.ref-box { background: #fff; border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 4px; padding: 0.75rem 1rem; margin: 1rem 0 1.5rem; }
.ref-box h3 { margin-top: 0; border: none; padding: 0; font-size: 0.95rem; color: var(--head); }
.ref-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1rem 0; }
.badge { display: inline-block; background: var(--accent); color: #fff; font-size: 0.75rem; font-weight: 600; padding: 1px 6px; border-radius: 3px; vertical-align: middle; margin-left: 4px; }
.badge.minor { background: #7a6a1a; }
.badge.major { background: #7a1a1a; }
code { background: #eef0f6; padding: 1px 5px; border-radius: 3px; font-size: 0.88em; }
@media print { body { background: #fff; } table { box-shadow: none; } h2 { background: #000; } .nav-bar { background: #000; } }
</style>"""
    )
    parts.append("</head>")
    parts.append("<body>")

    parts.append("<h1>Character Builder Reference Manual</h1>")
    parts.append(
        '<p class="lead">Savage Worlds Adventure Edition (SWADE) — Star Wars setting. '
        "Every option below is loaded live from the project's <code>data/</code> JSON files.</p>"
    )
    parts.append(
        '<p class="meta">&#x26A0; Regenerate this file whenever you edit a JSON data file: '
        "<code>python scripts/generate_character_manual.py</code></p>"
    )

    # Nav bar
    parts.append('<div class="nav-bar">')
    for label, anchor in [
        ("Species", "species"), ("Careers", "careers"), ("Hindrances", "hindrances"),
        ("Attributes", "attributes"), ("Skills", "skills"), ("Edges", "edges"),
        ("Weapons", "weapons"), ("Armor", "armor"), ("Attachments", "attachments"),
        ("Gear", "gear"), ("Mechanics", "mechanics"),
    ]:
        parts.append(f'<a href="#{anchor}">{label}</a>')
    parts.append("</div>")

    # Build flow
    parts.append("<h2>Build Flow (7 Steps)</h2>")
    parts.append("<ul class='steps'>")
    parts.append(
        "<li><strong>Step 1 — Concept:</strong> Choose a name, species, and career. "
        "Your species sets any racial traits and minimum attribute dice. "
        "Careers are free flavor packages — pick the one that fits the character concept.</li>"
    )
    parts.append(
        "<li><strong>Step 2 — Hindrances:</strong> Select up to <strong>4 hindrance points</strong> "
        "total (Major = 2 pts, Minor = 1 pt). These points are a currency you spend in steps 3–5.</li>"
    )
    parts.append(
        "<li><strong>Step 3 — Attributes:</strong> Spend <strong>5 free die steps</strong> across "
        "Agility, Smarts, Spirit, Strength, and Vigor (each starts at d4). "
        "Each step raises one attribute by one die (d4→d6→d8→d10→d12). "
        "Spend 2 hindrance points per extra step beyond the 5 free ones.</li>"
    )
    parts.append(
        "<li><strong>Step 4 — Skills:</strong> Spend <strong>15 free skill points</strong>. "
        "Core skills default to d4; all others start Untrained. "
        "Raising a skill up to its linked attribute costs 1 pt per step; "
        "above the linked attribute costs 2 pts per step. "
        "Spend hindrance points (1 pt each) for every skill point beyond 15.</li>"
    )
    parts.append(
        "<li><strong>Step 5 — Edges:</strong> Spend <strong>2 hindrance points per Edge</strong>. "
        "Humans get one free Edge (ignore requirements, except for prerequisite Edges). "
        "Edge requirements (rank, attribute, skill) must be met.</li>"
    )
    parts.append(
        "<li><strong>Step 6 — Equipment:</strong> Spend your starting credits on weapons (any number), "
        "one suit of armor, and general gear. Credits not spent carry over to play.</li>"
    )
    parts.append(
        "<li><strong>Step 7 — Summary &amp; Save:</strong> Review your derived stats "
        "(Toughness, Parry), confirm no validation errors, then save to <code>output/</code> as "
        "JSON, HTML sheet, and plain-text sheet.</li>"
    )
    parts.append("</ul>")

    # Mechanics reference
    parts.append('<h2 id="mechanics">Mechanics Quick Reference</h2>')
    parts.append('<div class="ref-grid">')

    # Point budget
    parts.append('<div class="ref-box">')
    parts.append("<h3>Hindrance Point Budget</h3>")
    parts.append(
        "<table><thead><tr><th>Phase</th><th>Free allowance</th><th>Hindrance cost to exceed</th></tr></thead><tbody>"
        "<tr><td>Attributes</td><td>5 die steps</td><td>2 pts per extra step</td></tr>"
        "<tr><td>Skills</td><td>15 skill points</td><td>1 pt per extra skill point</td></tr>"
        "<tr><td>Edges</td><td>0 (Human: 1 free)</td><td>2 pts per Edge</td></tr>"
        "</tbody></table>"
        "<p style='font-size:0.88rem;color:#555;'>Maximum hindrance points collectible: <strong>4</strong>.</p>"
    )
    parts.append("</div>")

    # Derived stats
    parts.append('<div class="ref-box">')
    parts.append("<h3>Derived Stats</h3>")
    parts.append(
        "<table><thead><tr><th>Stat</th><th>Formula</th></tr></thead><tbody>"
        "<tr><td><strong>Toughness</strong></td><td>2 + half Vigor die + armor bonus + size bonus</td></tr>"
        "<tr><td><strong>Parry</strong></td><td>2 + half Fighting die (or 2 if Untrained)</td></tr>"
        "<tr><td><strong>Pace</strong></td><td>6&Prime; (modified by some species)</td></tr>"
        "</tbody></table>"
        "<p style='font-size:0.88rem;color:#555;'>"
        "Half die = half the die's number, rounded down. Vigor d6 → 3; Vigor d8 → 4."
        "</p>"
    )
    parts.append("</div>")

    # Credits
    parts.append('<div class="ref-box">')
    parts.append("<h3>Starting Credits</h3>")
    parts.append(
        "<table><thead><tr><th>Condition</th><th>Credits</th></tr></thead><tbody>"
        "<tr><td>Standard (no wealth modifiers)</td><td>500 cr</td></tr>"
        "<tr><td>Poverty (Minor hindrance)</td><td>250 cr</td></tr>"
        "<tr><td>Poverty (Major hindrance)</td><td>125 cr</td></tr>"
        "<tr><td>Rich Edge</td><td>1,500 cr</td></tr>"
        "<tr><td>Filthy Rich Edge</td><td>2,500 cr</td></tr>"
        "</tbody></table>"
    )
    parts.append("</div>")

    # Skill cost
    parts.append('<div class="ref-box">')
    parts.append("<h3>Skill Point Cost per Step</h3>")
    parts.append(
        "<table><thead><tr><th>Skill die vs linked attribute</th><th>Cost per step</th></tr></thead><tbody>"
        "<tr><td>At or below linked attribute die</td><td>1 point</td></tr>"
        "<tr><td>Above linked attribute die</td><td>2 points</td></tr>"
        "<tr><td>Core skill (already at d4)</td><td>1 point to raise to d6+</td></tr>"
        "<tr><td>Species-granted skill</td><td>Counts from the granted die, not Untrained</td></tr>"
        "</tbody></table>"
    )
    parts.append("</div>")

    parts.append("</div>")  # /ref-grid

    # Species
    parts.append('<h2 id="species">Step 1 — Species</h2>')
    parts.append("<table>")
    parts.append(table_head(["Species", "Abilities", "Notes"]))
    parts.append("<tbody>")
    for name in sorted(species.keys(), key=str.lower):
        s = species[name]
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + esc(s.get("abilities", ""))
            + "</td><td>"
            + esc(s.get("notes", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Careers
    parts.append('<h2 id="careers">Step 1 — Careers</h2>')
    for cname in sorted(careers.keys(), key=str.lower):
        c = careers[cname]
        parts.append(f"<h3>{esc(cname)}</h3>")
        parts.append(f'<p class="career-desc">{esc(c.get("desc", ""))}</p>')
        parts.append("<table>")
        parts.append(table_head(["Benefit title", "Type", "Effect"]))
        parts.append("<tbody>")
        for b in c.get("benefits") or []:
            if not isinstance(b, dict):
                continue
            parts.append(
                "<tr><td>"
                + esc(b.get("title", ""))
                + "</td><td>"
                + esc(b.get("type", ""))
                + "</td><td>"
                + esc(b.get("effect", ""))
                + "</td></tr>"
            )
        parts.append("</tbody></table>")

    # Hindrances
    parts.append('<h2 id="hindrances">Step 2 — Hindrances</h2>')
    parts.append(
        "<p>Select up to <strong>4 hindrance points</strong>. Major hindrances = 2 pts each; "
        "Minor = 1 pt each. You may take up to 2 Major, or 1 Major + 2 Minor, or 4 Minor.</p>"
    )
    parts.append("<table>")
    parts.append(table_head(["Name", "Severity", "Pts", "Description"]))
    parts.append("<tbody>")
    for name, h in hind_rows:
        sev = h.get("type", "")
        badge_cls = "major" if sev == "Major" else "minor"
        badge = f'<span class="badge {badge_cls}">{esc(sev)}</span>'
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + badge
            + "</td><td><strong>"
            + esc(str(h.get("pts", "")))
            + "</strong></td><td>"
            + esc(h.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Attributes
    parts.append('<h2 id="attributes">Step 3 — Attributes</h2>')
    parts.append("<p>Die steps from d4 upward. Species may set minimum dice; the builder tracks free steps and hindrance cost for extra steps.</p>")
    parts.append("<table>")
    parts.append(table_head(["Attribute", "Typical use"]))
    parts.append("<tbody>")
    blurbs = {
        "Agility": "Nimbleness, ranged melee finesse, dodge, piloting, stealth.",
        "Smarts": "Reasoning, knowledge, technical skills, perception (Notice).",
        "Spirit": "Willpower, social presence, faith, intimidation.",
        "Strength": "Might, melee damage, athletic power.",
        "Vigor": "Endurance, health, resistance, base toughness.",
    }
    for a in attr_list:
        parts.append(
            "<tr><td><strong>"
            + esc(a)
            + "</strong></td><td>"
            + esc(blurbs.get(a, ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Skills
    parts.append('<h2 id="skills">Step 4 — Skills</h2>')
    parts.append(
        "<p>You have <strong>15 free skill points</strong>. "
        "Core skills already start at d4 and cost 1 pt per step to raise further. "
        "Non-core skills start Untrained; raising them up to their linked attribute costs 1 pt per step, "
        "above costs 2 pts per step. "
        "Species-granted skills begin at the granted die level at no cost.</p>"
    )
    parts.append("<table>")
    parts.append(table_head(["Skill", "Linked attribute", "Core (starts at d4)"]))
    parts.append("<tbody>")
    for sk, at in skill_rows:
        core_badge = '<span class="badge">Core</span>' if sk in core_skills else ""
        parts.append(
            "<tr><td><strong>"
            + esc(sk)
            + "</strong></td><td>"
            + esc(at)
            + "</td><td>"
            + core_badge
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Edges
    parts.append('<h2 id="edges">Step 5 — Edges</h2>')
    parts.append(
        "<p>Each Edge costs <strong>2 hindrance points</strong>. "
        "Humans get one free Novice Edge (prerequisite Edges must still be met). "
        "All attribute and skill requirements must be satisfied at the time of selection. "
        "New characters are Novice rank — only Novice (or no-rank) Edges are available at creation.</p>"
    )
    parts.append("<table>")
    parts.append(table_head(["Edge", "Requirements", "Description"]))
    parts.append("<tbody>")
    for ename, e in edge_rows:
        parts.append(
            "<tr><td><strong>"
            + esc(ename)
            + "</strong></td><td>"
            + esc(e.get("requirements", ""))
            + "</td><td>"
            + esc(e.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Weapons
    parts.append('<h2 id="weapons">Step 6 — Weapons</h2>')
    parts.append("<table>")
    parts.append(
        table_head(
            ["Name", "Cost", "Damage", "Range", "Hard P.", "Notes", "Description"]
        )
    )
    parts.append("<tbody>")
    for name, w in weapons:
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + esc(w.get("cost", ""))
            + "</td><td>"
            + esc(w.get("damage", ""))
            + "</td><td>"
            + esc(w.get("range", ""))
            + "</td><td>"
            + esc(w.get("hardPoints", "—"))
            + "</td><td>"
            + esc(w.get("notes", ""))
            + "</td><td>"
            + esc(w.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Armor
    parts.append('<h2 id="armor">Step 6 — Armor</h2>')
    parts.append("<table>")
    parts.append(
        table_head(["Name", "Cost", "Toughness", "Hard P.", "Notes", "Description"])
    )
    parts.append("<tbody>")
    for name, a in armor:
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + esc(a.get("cost", ""))
            + "</td><td>"
            + esc(a.get("toughness", ""))
            + "</td><td>"
            + esc(a.get("hardPoints", ""))
            + "</td><td>"
            + esc(a.get("notes", ""))
            + "</td><td>"
            + esc(a.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Attachments (hard points)
    parts.append(
        '<h2 id="attachments">Step 6 — Attachments (hard points)</h2>'
    )
    parts.append(
        "<p>Each attachment costs hard points from the base weapon or armor "
        "listed in <a href=\"#weapons\">Weapons</a> and <a href=\"#armor\">Armor</a>. "
        "Total attachment cost cannot exceed that item's hardPoints.</p>"
    )
    parts.append("<table>")
    parts.append(
        table_head(["Name", "Kind", "Cost (cr)", "HP cost", "Description", "Notes"])
    )
    parts.append("<tbody>")
    for aname, a in attach_rows:
        parts.append(
            "<tr><td><strong>"
            + esc(aname)
            + "</strong></td><td>"
            + esc(a.get("kind", ""))
            + "</td><td>"
            + esc(a.get("cost", ""))
            + "</td><td>"
            + esc(a.get("hardPointCost", ""))
            + "</td><td>"
            + esc(a.get("desc", ""))
            + "</td><td>"
            + esc(a.get("notes") or "")
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Gear
    parts.append('<h2 id="gear">Step 6 — General gear</h2>')
    parts.append("<table>")
    parts.append(table_head(["Name", "Cost", "Notes", "Description"]))
    parts.append("<tbody>")
    for name, g in ggear:
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + esc(g.get("cost", ""))
            + "</td><td>"
            + esc(g.get("notes", ""))
            + "</td><td>"
            + esc(g.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    parts.append("</body></html>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(parts)
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
