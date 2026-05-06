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
:root { --bg: #f6f7f9; --text: #1a1d26; --muted: #5c6578; --border: #c9ced9; --head: #2c3d5c; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.45; color: var(--text); background: var(--bg); margin: 0; padding: 1.5rem 2rem 3rem; max-width: 1200px; margin-left: auto; margin-right: auto; }
h1 { color: var(--head); font-size: 1.75rem; margin-top: 0; }
h2 { color: var(--head); font-size: 1.35rem; margin-top: 2.25rem; padding-bottom: 0.35rem; border-bottom: 2px solid var(--border); }
h3 { color: var(--head); font-size: 1.1rem; margin-top: 1.5rem; }
p.lead { color: var(--muted); font-size: 1.05rem; }
.meta { font-size: 0.9rem; color: var(--muted); margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.92rem; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
th, td { border: 1px solid var(--border); padding: 0.5rem 0.65rem; text-align: left; vertical-align: top; }
th { background: #e8ecf4; font-weight: 600; color: var(--head); }
tr:nth-child(even) td { background: #fafbfd; }
.career-desc { color: var(--muted); margin: 0.25rem 0 0.75rem; font-style: italic; }
ul.steps { margin: 0.5rem 0 1rem 1.2rem; }
ul.steps li { margin: 0.35rem 0; }
a.nav { color: #1d5a9c; }
@media print { body { background: #fff; } table { box-shadow: none; } }
</style>"""
    )
    parts.append("</head>")
    parts.append("<body>")

    parts.append("<h1>Character Builder Reference Manual</h1>")
    parts.append(
        '<p class="lead">Savage Worlds–style Star Wars character creation. '
        "Tables below list every option loaded from the project <code>data/</code> folder.</p>"
    )
    parts.append(
        f'<p class="meta">Regenerate this file after editing JSON: '
        f"<code>python scripts/generate_character_manual.py</code></p>"
    )

    parts.append("<h2>How to use this manual</h2>")
    parts.append("<ul class='steps'>")
    parts.append(
        "<li><strong>Step 1 — Concept:</strong> Choose name, species, and career (see tables below).</li>"
    )
    parts.append(
        "<li><strong>Step 2 — Hindrances:</strong> Up to 4 hindrance points total (Minor = 1, Major = 2). "
        "Points pay for higher attributes, extra skills, and edges.</li>"
    )
    parts.append(
        "<li><strong>Step 3 — Attributes:</strong> Agility, Smarts, Spirit, Strength, Vigor (dice d4–d12).</li>"
    )
    parts.append(
        "<li><strong>Step 4 — Skills:</strong> Train skills; core skills start at d4.</li>"
    )
    parts.append(
        "<li><strong>Step 5 — Edges:</strong> Special advantages; Humans get one free edge.</li>"
    )
    parts.append(
        "<li><strong>Step 6 — Equipment:</strong> Spend starting credits on weapons, one armor, and gear.</li>"
    )
    parts.append("</ul>")

    parts.append('<p>Jump to: ')
    parts.append(
        '<a class="nav" href="#species">Species</a> · '
        '<a class="nav" href="#careers">Careers</a> · '
        '<a class="nav" href="#hindrances">Hindrances</a> · '
        '<a class="nav" href="#attributes">Attributes</a> · '
        '<a class="nav" href="#skills">Skills</a> · '
        '<a class="nav" href="#edges">Edges</a> · '
        '<a class="nav" href="#weapons">Weapons</a> · '
        '<a class="nav" href="#armor">Armor</a> · '
        '<a class="nav" href="#gear">Gear</a>'
    )
    parts.append("</p>")

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
    parts.append("<table>")
    parts.append(table_head(["Name", "Severity", "Points", "Description"]))
    parts.append("<tbody>")
    for name, h in hind_rows:
        parts.append(
            "<tr><td><strong>"
            + esc(name)
            + "</strong></td><td>"
            + esc(h.get("type", ""))
            + "</td><td>"
            + esc(h.get("pts", ""))
            + "</td><td>"
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
        "<p>Core skills default to d4. Other skills default to Untrained until purchased. "
        "Linked attribute affects training cost.</p>"
    )
    parts.append("<table>")
    parts.append(table_head(["Skill", "Linked attribute", "Core skill"]))
    parts.append("<tbody>")
    for sk, at in skill_rows:
        core = "Yes" if sk in core_skills else ""
        parts.append(
            "<tr><td>"
            + esc(sk)
            + "</td><td>"
            + esc(at)
            + "</td><td>"
            + esc(core)
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Edges
    parts.append('<h2 id="edges">Step 5 — Edges</h2>')
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
        table_head(["Name", "Cost", "Damage", "Range", "Notes", "Description"])
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
            + esc(w.get("notes", ""))
            + "</td><td>"
            + esc(w.get("desc", ""))
            + "</td></tr>"
        )
    parts.append("</tbody></table>")

    # Armor
    parts.append('<h2 id="armor">Step 6 — Armor</h2>')
    parts.append("<table>")
    parts.append(table_head(["Name", "Cost", "Toughness", "Notes", "Description"]))
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
            + esc(a.get("notes", ""))
            + "</td><td>"
            + esc(a.get("desc", ""))
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
