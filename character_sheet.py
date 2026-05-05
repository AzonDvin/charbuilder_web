"""
Build human-readable character sheets from exported character JSON (dict).

Used by the GUI summary/export and by the CLI: ``python character_sheet.py <file.json>``.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path

from character import compute_display_toughness, size_toughness_bonus_from_species_abilities

try:
    from data import ARMOR, CAREERS, WEAPONS, GEAR
except ImportError:
    ARMOR = {}
    CAREERS = {}
    WEAPONS = {}
    GEAR = {}


def _equipment_notes_for(name: str) -> str:
    """Return trimmed notes text for a weapon, armor, or gear name from data tables."""
    if not name:
        return ""
    for source in (WEAPONS, ARMOR, GEAR):
        entry = source.get(name)
        if not entry:
            continue
        notes = entry.get("notes")
        if notes is None:
            return ""
        s = str(notes).strip()
        return s
    return ""


def _format_weapon_entry(name: str) -> str:
    """Name plus damage, range, and notes from gear data when available."""
    w = WEAPONS.get(name)
    if not w:
        return name
    dmg = str(w.get("damage") or "").strip()
    rng = str(w.get("range") or "").strip()
    notes = str(w.get("notes") or "").strip()
    bits = []
    if dmg:
        bits.append(dmg)
    if rng:
        bits.append(rng)
    if notes:
        bits.append(notes)
    if bits:
        return f"{name} — {', '.join(bits)}"
    return name


def _format_weapon_list(names: list[str]) -> str:
    if not names:
        return "None"
    return ", ".join(_format_weapon_entry(n) for n in names)


def _format_equipment_item_list(names: list[str]) -> str:
    """Comma-separated gear names with em dash + notes when notes exist in data."""
    if not names:
        return "None"
    parts = []
    for n in names:
        note = _equipment_notes_for(n)
        if note:
            parts.append(f"{n} — {note}")
        else:
            parts.append(n)
    return ", ".join(parts)


def _format_armor_value(armor_name: str) -> str:
    """Armor name with toughness modifier and optional notes from data."""
    label = armor_name or "No Armor"
    if label == "No Armor":
        return "No Armor"
    entry = ARMOR.get(label)
    if not entry:
        return label
    tough = str(entry.get("toughness", "") or "").strip()
    notes = str(entry.get("notes") or "").strip()
    out = label
    if tough and tough != "0":
        out = f"{label} ({tough} Tough)"
    if notes:
        out = f"{out} — {notes}"
    return out


def _split_skills_into_three_columns(skill_lines: list[str]) -> list[list[str]]:
    """Split skill lines into three columns with counts as equal as possible (remainder to left columns)."""
    n = len(skill_lines)
    if n == 0:
        return [[], [], []]
    base, rem = divmod(n, 3)
    sizes = [base + (1 if i < rem else 0) for i in range(3)]
    out: list[list[str]] = []
    idx = 0
    for sz in sizes:
        out.append(skill_lines[idx : idx + sz])
        idx += sz
    return out


def _career_lines_for_sheet(data: dict) -> list[str]:
    """Plain-text lines for career name, description, and every benefit."""
    name = (data.get("career") or "").strip()
    if not name:
        return []
    careers = CAREERS if isinstance(CAREERS, dict) else {}
    entry = careers.get(name)
    if not entry or not isinstance(entry, dict):
        return [f"CAREER: {name}", "  (no entry in careers data)"]
    out: list[str] = [f"CAREER: {name}"]
    desc = str(entry.get("desc") or "").strip()
    if desc:
        for part in desc.splitlines():
            out.append(f"  {part}" if part else "  ")
    benefits = entry.get("benefits")
    if isinstance(benefits, list):
        for b in benefits:
            if not isinstance(b, dict):
                continue
            title = str(b.get("title") or "").strip()
            eff = str(b.get("effect") or "").strip()
            typ = str(b.get("type") or "").strip()
            tag = f" [{typ}]" if typ else ""
            if title and eff:
                out.append(f"  • {title}{tag}: {eff}")
            elif title:
                out.append(f"  • {title}{tag}")
            elif eff:
                out.append(f"  • {eff}")
    return out


def _armor_toughness_bonus(armor_name: str) -> int:
    if not armor_name or armor_name not in ARMOR:
        return 0
    t = ARMOR[armor_name].get("toughness", "0")
    try:
        return int(str(t).replace("+", ""))
    except ValueError:
        return 0


def character_sheet_lines(data: dict) -> list[str]:
    """Return plain-text lines matching the in-app summary style."""
    name = data.get("name") or "(unnamed)"
    species = data.get("species") or "—"
    abilities = data.get("species_abilities") or "—"
    attributes = data.get("attributes") or {}
    skills = data.get("skills") or {}
    hindrances = data.get("hindrances") or []
    edges = data.get("edges") or []
    weapons = data.get("weapons") or []
    armor = data.get("armor") or "No Armor"
    gear = data.get("gear") or []
    credits = data.get("credits", 0)
    species_abilities_raw = data.get("species_abilities") or ""
    size_mod = size_toughness_bonus_from_species_abilities(species_abilities_raw)
    toughness = compute_display_toughness(attributes, armor, species_abilities_raw)
    parry = data.get("parry")
    armor_mod = _armor_toughness_bonus(armor)
    if size_mod:
        tough_detail = f"+{size_mod} Size, +{armor_mod} armor"
    else:
        tough_detail = f"+{armor_mod} armor"

    lines = [
        f"NAME: {name}",
        f"SPECIES: {species} ({abilities})",
    ]
    career_lines = _career_lines_for_sheet(data)
    if career_lines:
        lines.append("")
        lines.extend(career_lines)
    lines.extend(["", "ATTRIBUTES:"])
    for a, v in attributes.items():
        lines.append(f"  {a}: {v}")
    lines.extend(["", "SKILLS:"])
    for s, v in sorted(skills.items()):
        if v == "Untrained":
            continue
        lines.append(f"  {s}: {v}")
    lines.extend(
        [
            "",
            f"HINDRANCES: {', '.join(hindrances) or 'None'}",
            f"EDGES: {', '.join(edges) or 'None'}",
            "",
            f"WEAPONS: {_format_weapon_list(weapons)}",
            f"ARMOR: {_format_armor_value(armor)}",
            f"GEAR: {_format_equipment_item_list(gear)}",
            "",
            f"TOUGHNESS: {toughness} ({tough_detail})",
            f"PARRY: {parry}",
            f"CREDITS: {credits}",
        ]
    )
    human_used = data.get("human_free_edges_used") or []
    if human_used:
        lines.extend(["", f"HUMAN FREE EDGES USED: {', '.join(human_used)}"])
    return lines


def character_sheet_text(data: dict) -> str:
    return "\n".join(character_sheet_lines(data))


def _split_text_sheet_sections(
    lines: list[str],
) -> tuple[list[str], list[str], list[str], list[str]] | None:
    """Split plain sheet lines into head / attribute lines / skill lines / tail (same order as .txt)."""
    if "ATTRIBUTES:" not in lines:
        return None
    idx_attr = lines.index("ATTRIBUTES:")
    head = lines[:idx_attr]
    i = idx_attr + 1
    attr_lines: list[str] = []
    while i < len(lines) and lines[i] != "":
        attr_lines.append(lines[i])
        i += 1
    if i < len(lines) and lines[i] == "":
        i += 1
    skill_lines: list[str] = []
    if i < len(lines) and lines[i] == "SKILLS:":
        i += 1
        while i < len(lines) and lines[i] != "":
            skill_lines.append(lines[i])
            i += 1
    tail = lines[i:]
    return (head, attr_lines, skill_lines, tail)


def _pre_block(lines: list[str]) -> str:
    if not lines:
        return ""
    text = "\n".join(html.escape(line) for line in lines)
    return f'<pre class="txt-block">{text}</pre>'


def _split_tail_layout(
    tail: list[str],
) -> tuple[str, str, list[str], list[str], list[str]]:
    """Parse tail after skills to match ``character_sheet_lines`` ordering."""
    t = list(tail)
    i = 0
    while i < len(t) and t[i] == "":
        i += 1
    hind = t[i] if i < len(t) else "HINDRANCES: None"
    i += 1
    edges = t[i] if i < len(t) else "EDGES: None"
    i += 1
    while i < len(t) and t[i] == "":
        i += 1
    w = t[i] if i < len(t) else "WEAPONS: None"
    i += 1
    a = t[i] if i < len(t) else "ARMOR: No Armor"
    i += 1
    g = t[i] if i < len(t) else "GEAR: None"
    i += 1
    while i < len(t) and t[i] == "":
        i += 1
    tough = t[i] if i < len(t) else "TOUGHNESS: "
    i += 1
    par = t[i] if i < len(t) else "PARRY: "
    i += 1
    cred = t[i] if i < len(t) else "CREDITS: "
    i += 1
    remainder = t[i:]
    return (hind, edges, [w, a, g], [tough, par, cred], remainder)


def _pre_join_lines(lines: list[str]) -> str:
    return "\n".join(html.escape(line) for line in lines)


def _html_body_simpler(data: dict) -> str:
    """HTML sheet mirroring the .txt layout; attributes and skills share rows, skills in 3 balanced columns."""
    lines = character_sheet_lines(data)
    split = _split_text_sheet_sections(lines)
    if split is None:
        return f'<article class="sheet-txt">{_pre_block(lines)}</article>'
    head, attr_lines, skill_lines, tail = split

    skill_chunks = _split_skills_into_three_columns(skill_lines)
    max_chunk = max((len(c) for c in skill_chunks), default=0)
    n_rows = max(len(attr_lines), max_chunk, 1)

    row_cells = []
    for i in range(n_rows):
        left = html.escape(attr_lines[i]) if i < len(attr_lines) else ""
        chunk_cells = []
        for ci, chunk in enumerate(skill_chunks):
            cell = html.escape(chunk[i]) if i < len(chunk) else ""
            cls = "mono chunk-cell"
            if ci > 0:
                cls += " chunk-divider"
            chunk_cells.append(f'<div class="{cls}">{cell}</div>')
        right = (
            f'<div class="skills-inline-cols col-skills">'
            f'{"".join(chunk_cells)}</div>'
        )
        row_cells.append(f'<div class="mono attr-cell">{left}</div>{right}')
    rows_html = "\n".join(row_cells)

    head_html = _pre_block(head)
    hind, edges, equip_lines, derived_lines, tail_rest = _split_tail_layout(tail)
    hind_edges_html = f"""
      <div class="dual-row hind-edges" aria-label="Hindrances and edges">
        <pre class="mono-col">{html.escape(hind)}</pre>
        <pre class="mono-col col-b">{html.escape(edges)}</pre>
      </div>"""
    equip_derived_html = f"""
      <div class="dual-row equip-derived" aria-label="Equipment and derived stats">
        <pre class="mono-col">{_pre_join_lines(equip_lines)}</pre>
        <pre class="mono-col col-b">{_pre_join_lines(derived_lines)}</pre>
      </div>"""
    tail_html = _pre_block(tail_rest)

    return f"""
    <article class="sheet-txt">
      {head_html}
      <div class="attr-skills" aria-label="Attributes and skills">
        <div class="hdr">ATTRIBUTES:</div>
        <div class="hdr col-skills skills-hdr-right">SKILLS:</div>
        {rows_html}
      </div>
      {hind_edges_html}
      {equip_derived_html}
      {tail_html}
    </article>
    """


def character_sheet_html(data: dict, title: str | None = None) -> str:
    """Print-friendly HTML sheet: same content order as the .txt export; skills use three columns."""
    safe_title = html.escape(title or data.get("name") or "Character")
    body = _html_body_simpler(data)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
  :root {{
    --bg: #0f1115;
    --text: #e8eaed;
    --muted: #9aa0a6;
    --accent: #4a9eff;
    --border: #2d323c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.2;
    font-size: 11px;
  }}
  .wrap {{
    max-width: min(100%, 72rem);
    margin: 0 auto;
    padding: 6px 10px 12px;
  }}
  .sheet-txt {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.78rem;
    line-height: 1.22;
  }}
  .txt-block {{
    margin: 0 0 0.4em;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  .attr-skills {{
    display: grid;
    /* Narrow attributes; skills use the rest so long skill lines stay one line. */
    grid-template-columns: minmax(0, 10.5rem) minmax(0, 1fr);
    column-gap: 0.65rem;
    row-gap: 0;
    margin: 0.15em 0 0.5em;
    padding: 0.2em 0 0.35em;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    min-width: 0;
    overflow-x: auto;
  }}
  .attr-skills .hdr {{
    font-weight: 700;
    padding-bottom: 0.15em;
    margin-bottom: 0.1em;
    border-bottom: 1px solid var(--accent);
    color: var(--accent);
  }}
  .attr-skills .mono.attr-cell {{
    margin: 0;
    min-height: 1.22em;
    white-space: nowrap;
    overflow-x: auto;
    max-width: 100%;
  }}
  .attr-skills .col-skills,
  .attr-skills .skills-hdr-right {{
    border-left: 1px solid var(--border);
    padding-left: 0.75rem;
  }}
  .skills-inline-cols {{
    display: grid;
    grid-template-columns: repeat(3, minmax(11rem, 1fr));
    column-gap: 0.5rem;
    align-items: start;
    min-width: 0;
    overflow-x: auto;
  }}
  .skills-inline-cols .chunk-cell {{
    margin: 0;
    min-height: 1.22em;
    min-width: 0;
    white-space: nowrap;
    word-break: normal;
    overflow-wrap: normal;
    overflow-x: auto;
  }}
  .skills-inline-cols .chunk-divider {{
    border-left: 1px solid var(--border);
    padding-left: 0.65rem;
  }}
  .dual-row {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    column-gap: 1.25rem;
    row-gap: 0;
    margin: 0.35em 0 0.45em;
    padding: 0.2em 0 0.35em;
    border-bottom: 1px solid var(--border);
  }}
  .dual-row .mono-col {{
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: inherit;
  }}
  .dual-row .col-b {{
    border-left: 1px solid var(--border);
    padding-left: 0.75rem;
  }}
  @media (max-width: 520px) {{
    .attr-skills {{
      grid-template-columns: 1fr;
      column-gap: 0;
    }}
    .attr-skills .col-skills,
    .attr-skills .skills-hdr-right {{
      border-left: none;
      padding-left: 0;
      border-top: 1px solid var(--border);
      margin-top: 0.35em;
      padding-top: 0.35em;
    }}
    .skills-inline-cols {{
      overflow-x: auto;
      max-width: 100%;
      padding-bottom: 2px;
    }}
    .dual-row {{
      grid-template-columns: 1fr;
      column-gap: 0;
    }}
    .dual-row .col-b {{
      border-left: none;
      padding-left: 0;
      border-top: 1px solid var(--border);
      margin-top: 0.35em;
      padding-top: 0.35em;
    }}
  }}
  @media print {{
    @page {{ margin: 5mm; }}
    body {{ background: #fff; color: #000; font-size: 10px; }}
    .wrap {{ max-width: none; padding: 0; }}
    .attr-skills {{ border-color: #999; }}
    .attr-skills .hdr {{ color: #000; border-color: #1a5276; }}
    .attr-skills .col-skills,
    .attr-skills .skills-hdr-right {{ border-color: #bbb; }}
    .skills-inline-cols .chunk-divider {{ border-color: #bbb; }}
    .dual-row {{ border-color: #999; }}
    .dual-row .col-b {{ border-color: #bbb; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    {body}
  </div>
</body>
</html>
"""


def load_character_json(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a character JSON export as HTML or plain text for viewing/printing.",
    )
    parser.add_argument("json_file", type=Path, help="Path to exported character .json")
    parser.add_argument(
        "--html",
        type=Path,
        metavar="FILE",
        help="Write a print-friendly HTML sheet to FILE",
    )
    parser.add_argument(
        "--text",
        type=Path,
        metavar="FILE",
        help="Write a plain-text sheet to FILE",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print plain-text sheet to stdout (same as --text -)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML output in the default browser (requires --html)",
    )
    args = parser.parse_args(argv)

    if args.open and not args.html:
        parser.error("--open requires --html")

    data = load_character_json(args.json_file)
    text = character_sheet_text(data)

    if args.stdout:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")

    if args.text:
        out = args.text
        if str(out) == "-":
            sys.stdout.write(text)
            if not text.endswith("\n"):
                sys.stdout.write("\n")
        else:
            out.write_text(text, encoding="utf-8")

    if args.html:
        html_out = character_sheet_html(data)
        args.html.write_text(html_out, encoding="utf-8")
        if args.open:
            webbrowser.open(_file_uri(args.html))

    if not args.stdout and not args.text and not args.html:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        print(
            "\n---\nTip: use --html sheet.html for a printable layout, "
            "or --html sheet.html --open to view in your browser.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
