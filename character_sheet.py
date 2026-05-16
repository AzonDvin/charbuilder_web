"""
Build human-readable character sheets from exported character JSON (dict).

Used by the web API and by the CLI: ``python character_sheet.py <file.json>``.
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
    rng_clean = rng.replace("-", "").replace("/", "").strip()
    bits = []
    if dmg:
        bits.append(dmg)
    if rng and rng_clean:
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
    label = (armor_name or "").strip()
    if not label:
        return "None"
    if label == "No Armor":
        return "None"
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
    """Plain-text lines for career name and every benefit (career `desc` is not printed)."""
    name = (data.get("career") or "").strip()
    if not name:
        return []
    careers = CAREERS if isinstance(CAREERS, dict) else {}
    entry = careers.get(name)
    if not entry or not isinstance(entry, dict):
        return [f"CAREER: {name}", "  (no entry in careers data)"]
    out: list[str] = [f"CAREER: {name}"]
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
    armor = (data.get("armor") or "").strip()
    if armor == "No Armor":
        armor = ""
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
    a = t[i] if i < len(t) else "ARMOR: None"
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
    """Print-friendly HTML styled like the official Savage Worlds Star Wars record sheet."""
    from collections import defaultdict

    E = html.escape

    # ── Data extraction ───────────────────────────────────────────────────
    char_name    = data.get("name") or "(unnamed)"
    species_name = data.get("species") or "—"
    career_name  = data.get("career") or "—"
    attributes   = data.get("attributes") or {}
    skills       = data.get("skills") or {}
    hindrances   = data.get("hindrances") or []
    edges        = data.get("edges") or []
    weapons_list = data.get("weapons") or []
    armor_name   = (data.get("armor") or "").strip()
    if armor_name == "No Armor":
        armor_name = ""
    gear_list    = data.get("gear") or []
    credits_left = data.get("credits", 0)
    species_ab   = data.get("species_abilities") or ""
    toughness    = compute_display_toughness(attributes, armor_name, species_ab)
    parry        = data.get("parry") or "—"
    human_free   = data.get("human_free_edges_used") or []

    try:
        from data import SKILL_ATTRIBUTES as _SA, EDGES as _ED, CAREERS as _CA
        skill_attr_map: dict = _SA
        edges_data: dict     = _ED
        careers_data: dict   = _CA
    except ImportError:
        skill_attr_map = {}
        edges_data     = {}
        careers_data   = {}

    def die_track(cur: str) -> str:
        label = cur if cur.startswith("d") else f"d{cur}"
        return f'<span class="die-badge">{E(label)}</span>'

    # ── Attributes HTML ───────────────────────────────────────────────────
    ATTR_DEFS = [
        ("Agility",  "AGI", "lity"),
        ("Smarts",   "SMA", "rts"),
        ("Spirit",   "SPI", "rit"),
        ("Strength", "STR", "ength"),
        ("Vigor",    "VIG", "or"),
    ]
    attr_rows_html = ""
    for attr, short, rest in ATTR_DEFS:
        val = attributes.get(attr, "d4")
        attr_rows_html += (
            f'<div class="attr-row">'
            f'<span class="al"><b>{short}</b><sup>{rest}</sup></span>'
            f'{die_track(val)}'
            f'</div>'
        )

    # ── Skills HTML ───────────────────────────────────────────────────────
    skill_rows_html = ""
    for sk in sorted(skills.keys()):
        val = skills[sk]
        if val == "Untrained":
            continue
        gov  = skill_attr_map.get(sk, "")
        abbr = gov[:3].upper() if gov else ""
        skill_rows_html += (
            f'<div class="sk-row">'
            f'<span class="sn">{E(sk)}</span>'
            f'<span class="sa">{abbr}</span>'
            f'{die_track(val)}'
            f'</div>'
        )

    # ── Hindrances HTML ───────────────────────────────────────────────────
    hind_parts = [f'<div class="hind-line">{E(h)}</div>' for h in hindrances]
    for _ in range(max(0, 5 - len(hindrances))):
        hind_parts.append('<div class="hind-line">&nbsp;</div>')
    hind_html = "".join(hind_parts)

    # ── Edges HTML (by tier) ──────────────────────────────────────────────
    TIERS = ["Novice", "Seasoned", "Veteran", "Heroic", "Legendary"]

    def edge_rank(ename: str) -> str:
        reqs = (edges_data.get(ename) or {}).get("requirements", "")
        for t in TIERS:
            if t.lower() in reqs.lower():
                return t
        return "Novice"

    by_tier: dict = defaultdict(list)
    starting_edges = [e for e in edges if e in human_free]
    for e in edges:
        if e not in human_free:
            by_tier[edge_rank(e)].append(e)

    edge_parts = ['<div class="edge-tier-lbl">Starting &amp; Racials</div>']
    for e in starting_edges:
        edge_parts.append(f'<div class="edge-line">{E(e)}</div>')
    for _ in range(max(1, 2 - len(starting_edges))):
        edge_parts.append('<div class="edge-line">&nbsp;</div>')
    for tier in TIERS:
        edge_parts.append(f'<div class="edge-tier-lbl">{E(tier)}</div>')
        tier_list = by_tier.get(tier, [])
        for e in tier_list:
            edge_parts.append(f'<div class="edge-line">{E(e)}</div>')
        for _ in range(max(1, 3 - len(tier_list))):
            edge_parts.append('<div class="edge-line">&nbsp;</div>')
    edges_html = "".join(edge_parts)

    # ── Career benefits HTML ──────────────────────────────────────────────
    career_entry = (careers_data.get(career_name) or {}) if isinstance(careers_data, dict) else {}
    benefits = career_entry.get("benefits", []) if isinstance(career_entry, dict) else []
    career_ben_html = ""
    for b in benefits[:5]:
        if isinstance(b, dict):
            t  = b.get("title", "")
            ef = b.get("effect", "")
            if t:
                career_ben_html += f'<div class="ben-line">&#x25CF; {E(t)}: {E(ef)}</div>'

    # ── Weapons HTML ──────────────────────────────────────────────────────
    def weapon_block(wname: str | None) -> str:
        if wname:
            w     = (WEAPONS or {}).get(wname, {})
            dmg   = E(str(w.get("damage", "")).strip())
            rng   = E(str(w.get("range",  "")).strip())
            notes = E(str(w.get("notes",  "")).strip())
            main = (
                f'<div class="wc wn">{E(wname)}</div>'
                f'<div class="wc">{rng}</div>'
                f'<div class="wc">&#x2014;</div>'
                f'<div class="wc">{dmg}</div>'
            )
            sub = (
                f'<div class="wcs">AMMO</div>'
                f'<div class="wcs">LOCATION</div>'
                f'<div class="wcs">WEIGHT</div>'
                f'<div class="wcs">TYPE</div>'
                f'<div class="wcs wcs-notes">{notes}</div>'
            )
        else:
            main = (
                '<div class="wc wn">&nbsp;</div>'
                '<div class="wc"></div><div class="wc"></div><div class="wc"></div>'
            )
            sub = (
                '<div class="wcs">AMMO</div>'
                '<div class="wcs">LOCATION</div>'
                '<div class="wcs">WEIGHT</div>'
                '<div class="wcs">TYPE</div>'
                '<div class="wcs wcs-notes"></div>'
            )
        return (
            f'<div class="w-main">{main}</div>'
            f'<div class="w-sub">{sub}</div>'
        )

    n_weapon_slots = max(2, len(weapons_list))
    weapons_html = "".join(
        weapon_block(weapons_list[i] if i < len(weapons_list) else None)
        for i in range(n_weapon_slots)
    )

    # ── Gear HTML ─────────────────────────────────────────────────────────
    gear_parts = [
        f'<div class="gear-row"><div class="gc">{E(g)}</div><div class="gc-wt"></div></div>'
        for g in gear_list
    ]
    for _ in range(max(0, 6 - len(gear_parts))):
        gear_parts.append('<div class="gear-row"><div class="gc">&nbsp;</div><div class="gc-wt"></div></div>')
    gear_html = "".join(gear_parts)

    # ── Armor ─────────────────────────────────────────────────────────────
    armor_tn    = f'+{_armor_toughness_bonus(armor_name)}' if armor_name else ""
    armor_disp  = E(armor_name) if armor_name else "&#x2014;"
    armor_notes = E(_equipment_notes_for(armor_name)) if armor_name else ""

    safe_title_str = E(title or char_name)
    abilities_html = E(species_ab) if species_ab else "&nbsp;"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title_str}</title>
<style>
  @page {{ size: letter portrait; margin: 5mm; }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 7.5pt; background: #fff; color: #000; line-height: 1.25; }}
  .sheet {{ width: 100%; max-width: 740px; margin: 0 auto; border: 2px solid #000; background: #fff; }}

  /* Header */
  .hf {{ padding: 2px 5px; border-right: 1px solid #444; min-height: 18px; display: flex; flex-direction: column; justify-content: flex-end; background: #1a3a6b; color: #fff; }}
  .hf:last-child {{ border-right: none; }}
  .hl {{ font-size: 5pt; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }}
  .hv {{ font-size: 8.5pt; font-weight: bold; min-height: 11px; }}

  /* Section header bars */
  .sec-hdr {{ background: #1a3a6b; color: #fff; font-size: 7pt; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px; padding: 2px 5px; }}

  /* Main layout */
  .main-body {{ display: grid; grid-template-columns: 215px 1fr; border-top: 2px solid #000; }}
  .left-panel {{ border-right: 2px solid #000; }}
  .right-panel {{ display: grid; grid-template-columns: 1fr 185px; }}
  .center-panel {{ border-right: 1px solid #000; }}

  /* Die badge */
  .die-badge {{ display: inline-block; background: #1a3a6b; color: #fff; font-size: 7pt; font-weight: bold; padding: 1px 4px; border-radius: 3px; flex-shrink: 0; letter-spacing: 0.5px; }}

  /* Attributes */
  .attr-row {{ display: flex; align-items: center; gap: 4px; padding: 3px 5px; border-bottom: 1px solid #ddd; }}
  .al {{ width: 46px; font-size: 8.5pt; font-weight: bold; flex-shrink: 0; text-transform: uppercase; }}
  .al sup {{ font-size: 5pt; font-weight: normal; }}

  /* Skills */
  .sk-row {{ display: flex; align-items: center; gap: 2px; padding: 1.5px 5px; border-bottom: 1px solid #eee; min-height: 13px; }}
  .sn {{ flex: 1; font-size: 7pt; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .sa {{ font-size: 5.5pt; color: #666; width: 22px; text-align: right; flex-shrink: 0; }}

  /* Derived stats */
  .ds-box {{ display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-bottom: 1px solid #ddd; }}
  .ds-lbl {{ background: #1a3a6b; color: #fff; font-size: 7pt; font-weight: bold; padding: 2px 4px; text-transform: uppercase; letter-spacing: 0.5px; min-width: 70px; text-align: center; flex-shrink: 0; }}
  .ds-val {{ font-size: 16pt; font-weight: bold; line-height: 1; min-width: 26px; text-align: center; border-bottom: 2px solid #000; }}
  .ds-note {{ font-size: 5.5pt; color: #555; line-height: 1.3; }}

  /* Wounds / Fatigue */
  .wound-row {{ display: flex; gap: 4px; padding: 3px 5px 4px; flex-wrap: wrap; }}
  .wbub {{ width: 22px; height: 22px; border-radius: 50%; border: 2px solid #000; display: flex; align-items: center; justify-content: center; font-size: 7pt; font-weight: bold; flex-shrink: 0; }}

  /* Hindrances */
  .hind-line {{ padding: 2px 5px; border-bottom: 1px solid #ccc; min-height: 13px; font-size: 7pt; }}

  /* Edges */
  .edge-tier-lbl {{ font-size: 5.5pt; color: #888; padding: 1px 5px; border-bottom: 1px solid #eee; text-transform: uppercase; letter-spacing: 0.5px; }}
  .edge-line {{ font-size: 7pt; padding: 2px 5px; border-bottom: 1px solid #eee; min-height: 13px; }}

  /* Career */
  .ben-line {{ font-size: 6pt; padding: 1px 5px; border-bottom: 1px solid #eee; }}

  /* Abilities */
  .ab-box {{ padding: 3px 5px; font-size: 6pt; color: #333; min-height: 24px; border-bottom: 2px solid #000; background: #f8f8f8; }}

  /* Bottom split */
  .bottom-section {{ display: grid; grid-template-columns: 1fr 1fr; border-top: 2px solid #000; }}
  .weapons-section {{ border-right: 1px solid #000; }}

  /* Weapon rows */
  .w-hdr {{ display: grid; grid-template-columns: 1fr 65px 38px 70px; background: #1a3a6b; color: #fff; border-bottom: 1px solid #000; }}
  .w-main {{ display: grid; grid-template-columns: 1fr 65px 38px 70px; border-bottom: 1px solid #aaa; min-height: 16px; }}
  .w-sub {{ display: grid; grid-template-columns: repeat(4,1fr) 1.5fr; border-bottom: 2px solid #000; background: #f5f5f5; }}
  .wc {{ padding: 2px 3px; border-right: 1px solid #ccc; font-size: 7pt; }}
  .wc:last-child {{ border-right: none; }}
  .wn {{ font-weight: bold; }}
  .w-hdr .wc {{ border-color: #555; font-size: 6pt; font-weight: bold; }}
  .wcs {{ padding: 1px 3px; border-right: 1px solid #ccc; font-size: 5.5pt; color: #777; text-transform: uppercase; }}
  .wcs:last-child {{ border-right: none; }}
  .wcs-notes {{ font-size: 6pt; color: #333; text-transform: none; }}

  /* Gear */
  .gear-hdr {{ display: flex; justify-content: space-between; align-items: center; background: #1a3a6b; color: #fff; font-size: 10pt; font-weight: 900; letter-spacing: 2px; padding: 2px 6px; text-transform: uppercase; }}
  .gear-col-hdr {{ display: grid; grid-template-columns: 1fr 40px; background: #2a4f8a; color: #fff; border-bottom: 1px solid #000; }}
  .gchl {{ padding: 1px 3px; font-size: 5.5pt; border-right: 1px solid #555; }}
  .gchw {{ padding: 1px 3px; font-size: 5.5pt; }}
  .gear-row {{ display: grid; grid-template-columns: 1fr 40px; border-bottom: 1px solid #ddd; min-height: 13px; }}
  .gc {{ padding: 1px 3px; border-right: 1px solid #ddd; font-size: 7pt; }}
  .gc-wt {{ padding: 1px 3px; font-size: 7pt; }}

  /* Armor */
  .armor-hdr {{ display: grid; grid-template-columns: 1fr 44px 28px 52px; background: #1a3a6b; color: #fff; border-bottom: 1px solid #000; border-top: 1px solid #000; }}
  .armor-row {{ display: grid; grid-template-columns: 1fr 44px 28px 52px; border-bottom: 1px solid #ccc; min-height: 14px; }}
  .ac {{ padding: 2px 3px; border-right: 1px solid #ccc; font-size: 7pt; }}
  .ac:last-child {{ border-right: none; }}
  .armor-hdr .ac {{ font-size: 5.5pt; font-weight: bold; border-color: #555; }}

  /* Credits bar */
  .cred-bar {{ background: #1a3a6b; color: #fff; padding: 3px 6px; font-size: 8pt; font-weight: bold; display: flex; justify-content: space-between; border-top: 2px solid #000; }}

  @media print {{
    @page {{ size: letter portrait; margin: 5mm; }}
    .sheet {{ border: 1.5px solid #000; max-width: none; }}
  }}
</style>
</head>
<body>
<div class="sheet">

  <!-- ── Header ── -->
  <div style="display:grid;grid-template-columns:1fr 165px;background:#1a3a6b;border-bottom:2px solid #000;">
    <div>
      <div style="display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid #333;">
        <div class="hf"><div class="hl">Hero</div><div class="hv">{E(char_name)}</div></div>
        <div class="hf"><div class="hl">Archtype</div><div class="hv">{E(career_name)}</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1.2fr 1.2fr 0.8fr 0.8fr;border-bottom:1px solid #333;">
        <div class="hf"><div class="hl">Setting</div><div class="hv" style="font-size:7.5pt;">Star Wars</div></div>
        <div class="hf"><div class="hl">Species</div><div class="hv" style="font-size:7.5pt;">{E(species_name)}</div></div>
        <div class="hf"><div class="hl">Rank</div><div class="hv" style="font-size:7.5pt;">Novice</div></div>
        <div class="hf"><div class="hl">Total XP</div><div class="hv" style="font-size:7.5pt;">0</div></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(7,1fr);">
        <div class="hf"><div class="hl">Age</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf"><div class="hl">Gender</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf"><div class="hl">Height</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf"><div class="hl">Weight</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf"><div class="hl">Eyes</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf"><div class="hl">Hair</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
        <div class="hf" style="border-right:none;"><div class="hl">Skin</div><div class="hv" style="font-size:7pt;min-height:12px;"></div></div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;border-left:1px solid #444;padding:4px 8px;background:#1a3a6b;color:#fff;">
      <div style="font-size:8.5pt;font-weight:900;font-style:italic;letter-spacing:3px;color:#ddd;">SAVAGE!</div>
      <div style="font-size:19pt;font-weight:900;line-height:1.0;text-align:center;letter-spacing:1px;">STAR<br>WARS</div>
      <div style="font-size:5pt;margin-top:4px;letter-spacing:1px;text-align:center;color:#aaa;text-transform:uppercase;">Character Record Sheet</div>
    </div>
  </div>

  <!-- ── Main body ── -->
  <div class="main-body">

    <!-- Left panel: Attributes + Skills -->
    <div class="left-panel">
      <div class="sec-hdr">&#x2013; Attributes &#x2013;</div>
      {attr_rows_html}
      <div class="ab-box">
        <div style="font-size:5.5pt;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:1px;">Species Abilities</div>
        {abilities_html}
      </div>
      <div class="sec-hdr">&#x2013; Skills &#x2013;</div>
      {skill_rows_html}
    </div>

    <!-- Right panel -->
    <div class="right-panel">

      <!-- Center panel: derived stats + wounds + hindrances + career -->
      <div class="center-panel">

        <div class="ds-box">
          <span class="ds-lbl">Pace</span>
          <span class="ds-val">6</span>
          <span class="ds-note">[ 6&Prime; ]</span>
        </div>
        <div class="ds-box">
          <span class="ds-lbl">Parry</span>
          <span class="ds-val">{E(str(parry))}</span>
          <span class="ds-note">2+Half<br>Fighting</span>
        </div>
        <div class="ds-box">
          <span class="ds-lbl">Toughness</span>
          <span class="ds-val">{E(str(toughness))}</span>
          <span class="ds-note">2+Half<br>Vigor</span>
        </div>

        <div style="border-top:1px solid #bbb;">
          <div class="sec-hdr" style="font-size:6pt;">Wounds</div>
          <div class="wound-row">
            <div class="wbub">-1</div>
            <div class="wbub">-2</div>
            <div class="wbub">-3</div>
            <div class="wbub" style="font-size:6pt;border-style:dashed;">OUT</div>
          </div>
        </div>

        <div style="border-top:1px solid #bbb;">
          <div class="sec-hdr" style="font-size:6pt;">Fatigue</div>
          <div class="wound-row">
            <div class="wbub">-1</div>
            <div class="wbub">-2</div>
          </div>
        </div>

        <div style="border-top:1px solid #bbb;padding:2px 5px 4px;">
          <div style="font-size:5.5pt;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Permanent Injuries</div>
          <div style="border-bottom:1px solid #ccc;min-height:11px;">&nbsp;</div>
          <div style="border-bottom:1px solid #ccc;min-height:11px;">&nbsp;</div>
          <div style="border-bottom:1px solid #ccc;min-height:11px;">&nbsp;</div>
        </div>

        <div style="border-top:2px solid #000;margin-top:4px;">
          <div class="sec-hdr">&#x2013; Hindrances &#x2013;</div>
          {hind_html}
        </div>

        <div style="border-top:2px solid #000;margin-top:4px;">
          <div class="sec-hdr">Career</div>
          <div style="font-size:8pt;font-weight:bold;padding:2px 5px;">{E(career_name)}</div>
          {career_ben_html}
        </div>

        <div style="border-top:1px solid #ccc;padding:3px 5px;margin-top:4px;">
          <div style="font-size:5.5pt;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Credits Remaining</div>
          <div style="font-size:12pt;font-weight:bold;">{E(str(credits_left))}</div>
        </div>

      </div><!-- /center-panel -->

      <!-- Edge panel -->
      <div>
        <div class="sec-hdr">Edges</div>
        {edges_html}
      </div>

    </div><!-- /right-panel -->
  </div><!-- /main-body -->

  <!-- ── Bottom: Weapons | Gear + Armor ── -->
  <div class="bottom-section">

    <div class="weapons-section">
      <div class="w-hdr">
        <div class="wc">Weapon</div>
        <div class="wc">Range</div>
        <div class="wc">ROF</div>
        <div class="wc">Damage</div>
      </div>
      {weapons_html}
    </div>

    <div>
      <div class="gear-hdr"><span>Gear</span><span style="font-size:6pt;font-weight:normal;">WT</span></div>
      <div class="gear-col-hdr"><div class="gchl">Item</div><div class="gchw">WT</div></div>
      {gear_html}
      <div class="armor-hdr">
        <div class="ac">Armor</div><div class="ac">Type</div><div class="ac">TN</div><div class="ac">Area</div>
      </div>
      <div class="armor-row">
        <div class="ac">{armor_disp}</div>
        <div class="ac"></div>
        <div class="ac">{armor_tn}</div>
        <div class="ac">{armor_notes}</div>
      </div>
      <div class="armor-row">
        <div class="ac">&nbsp;</div><div class="ac"></div><div class="ac"></div><div class="ac"></div>
      </div>
    </div>

  </div><!-- /bottom-section -->

  <div class="cred-bar">
    <span>Credits: {E(str(credits_left))}</span>
    <span style="font-size:5.5pt;font-weight:normal;color:#aaa;">Savage Worlds Star Wars &#x2022; charbuilder</span>
  </div>

</div><!-- /sheet -->
</body>
</html>"""


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
