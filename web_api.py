"""
Local FastAPI web UI: single top-down character builder page.
Saves exports under ./output/ on the machine running the server.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from character import (
    Character,
    merge_species_attribute_minimums,
    parse_species_granted_skill_dice,
)
from character_sheet import character_sheet_html, character_sheet_text
from data import (
    ARMOR,
    ATTRIBUTES,
    CAREERS,
    CORE_SKILLS,
    EDGES,
    GEAR,
    HINDRANCES,
    SKILL_ATTRIBUTES,
    SPECIES,
    WEAPONS,
)
from rules import (
    attribute_steps_billable,
    attribute_steps_spent,
    edge_missing_attribute_requirements,
    edge_missing_skill_requirements,
    get_base_credits,
    hindrance_points_after_skills,
    hindrance_points_on_attributes,
    recalc_credits,
    total_adjusted_skill_cost,
    validate_hindrance_budget,
)

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"
STATIC_DIR = ROOT_DIR / "static"
TEMPLATES_DIR = ROOT_DIR / "templates"


def _gear_entries_sorted_by_cost(entries: dict) -> list[tuple[str, dict]]:
    """Name → data dict, ascending by credit cost then name."""
    return sorted(
        entries.items(),
        key=lambda x: (x[1].get("cost", 0) if isinstance(x[1], dict) else 0, str(x[0]).lower()),
    )


def _safe_filename_base(name: str) -> str:
    base = (name or "character").strip() or "character"
    for c in '\\/:*?"<>|':
        base = base.replace(c, "_")
    return base


def _die_to_num(die: str) -> int:
    return {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}.get(die, 4)


def _num_to_die(num: int) -> str:
    return {4: "d4", 6: "d6", 8: "d8", 10: "d10", 12: "d12"}.get(num, "d4")


def normalize_skills_for_species(char: Character) -> None:
    """Apply species skill dice grants (same behavior as the Tkinter skills step)."""
    core = set(CORE_SKILLS)
    for s in CORE_SKILLS:
        if s not in char.skills:
            char.skills[s] = "d4"

    grants = parse_species_granted_skill_dice(
        char.species_abilities, SKILL_ATTRIBUTES.keys()
    )
    for sk, g_die in grants.items():
        cur = char.skills.get(sk, "Untrained" if sk not in core else "d4")
        if cur == "Untrained":
            char.skills[sk] = g_die
        else:
            char.skills[sk] = _num_to_die(max(_die_to_num(cur), _die_to_num(g_die)))


def hydrate_character(data: dict) -> Character:
    """Payload → Character with species text, normalized skills, credits."""
    char = Character.from_dict(data or {})
    sp = char.species
    if sp and sp in SPECIES:
        char.species_abilities = SPECIES[sp].get("abilities", "")
    merge_species_attribute_minimums(char)
    normalize_skills_for_species(char)
    recalc_credits(char)
    return char


def edges_meeting_trait_requirements(char: Character) -> list[str]:
    """Edge names whose attribute and skill requirements are satisfied (for Human free-edge list)."""
    eligible: list[str] = []
    for name, ed in EDGES.items():
        if edge_missing_attribute_requirements(ed, char.attributes):
            continue
        if edge_missing_skill_requirements(ed, char.skills, SKILL_ATTRIBUTES):
            continue
        eligible.append(name)
    return sorted(eligible, key=str.lower)


def compute_budget_totals(char: Character) -> dict:
    """
    Running totals for the live panel (matches wizard math: hindrances → attributes → skills → edges).
    """
    H_total = sum(HINDRANCES[h]["pts"] for h in char.hindrances if h in HINDRANCES)
    raw_attr_steps = attribute_steps_spent(char.attributes, ATTRIBUTES)
    bill_attr_steps = attribute_steps_billable(
        char.attributes, ATTRIBUTES, char.species_abilities
    )
    h_on_attr = hindrance_points_on_attributes(bill_attr_steps)
    h_after_attr = H_total - h_on_attr
    skill_total = total_adjusted_skill_cost(
        char.skills,
        char.attributes,
        CORE_SKILLS,
        SKILL_ATTRIBUTES,
        char.species_abilities,
    )
    skill_over_base = max(0, skill_total - 15)
    h_after_skills = hindrance_points_after_skills(h_after_attr, skill_total)
    known_edges = [e for e in char.edges if e in EDGES]
    paid_edges = [e for e in known_edges if e not in char.human_free_edges_used]
    h_on_edges = 2 * len(paid_edges)
    h_remaining_after_edges = h_after_skills - h_on_edges
    skill_budget = 15 + max(0, h_after_attr)

    return {
        "hindrance_points_from_hindrances": H_total,
        "hindrance_points_max": 4,
        "attribute_die_steps": raw_attr_steps,
        "attribute_steps_billable": bill_attr_steps,
        "species_attribute_steps_gift": max(0, raw_attr_steps - bill_attr_steps),
        "attribute_free_steps": 5,
        "hindrance_spent_on_attributes": h_on_attr,
        "hindrance_pool_after_attributes": h_after_attr,
        "skill_points_budget": skill_budget,
        "skill_points_spent": skill_total,
        "skill_points_remaining": skill_budget - skill_total,
        "hindrance_used_by_skills_past_15": skill_over_base,
        "hindrance_pool_after_skills": h_after_skills,
        "edges_selected": len(char.edges),
        "edges_paid_with_hindrance": len(paid_edges),
        "hindrance_spent_on_edges": h_on_edges,
        "hindrance_pool_after_edges": h_remaining_after_edges,
        "human_species": char.species == "Human",
        "human_free_edge_slots": 1 if char.species == "Human" else 0,
        "human_free_edges_applied": len(char.human_free_edges_used),
        "starting_credits": get_base_credits(char),
        "credits_remaining": char.credits,
        "toughness": char.get_toughness(),
        "parry": char.get_parry(),
    }


def validate_character(char: Character) -> list[str]:
    """Return human-readable validation errors (empty if the build is consistent)."""
    errors: list[str] = []
    sp_name = (char.species or "").strip()
    if not sp_name:
        errors.append("Choose a species.")
    elif sp_name not in SPECIES:
        errors.append(f"Unknown species: {sp_name}")

    cr_name = (getattr(char, "career", None) or "").strip()
    if not cr_name:
        errors.append("Choose a career.")
    elif cr_name not in CAREERS:
        errors.append(f"Unknown career: {cr_name}")

    for e in char.edges:
        if e not in EDGES:
            errors.append(f"Unknown edge: {e}")

    for w in char.weapons:
        if w not in WEAPONS:
            errors.append(f"Unknown weapon: {w}")

    if char.armor and char.armor not in ARMOR:
        errors.append(f"Unknown armor: {char.armor}")

    for g in char.gear:
        if g not in GEAR:
            errors.append(f"Unknown gear item: {g}")

    bill_attr_steps = attribute_steps_billable(
        char.attributes, ATTRIBUTES, char.species_abilities
    )
    skill_total = total_adjusted_skill_cost(
        char.skills,
        char.attributes,
        CORE_SKILLS,
        SKILL_ATTRIBUTES,
        char.species_abilities,
    )

    h_errors, *_rest = validate_hindrance_budget(
        char.hindrances,
        bill_attr_steps,
        skill_total,
        char.edges,
        char.human_free_edges_used,
        char.species,
    )
    errors.extend(h_errors)

    for edge_name in char.edges:
        ed = EDGES.get(edge_name, {})
        miss = edge_missing_attribute_requirements(ed, char.attributes)
        miss += edge_missing_skill_requirements(ed, char.skills, SKILL_ATTRIBUTES)
        if miss:
            errors.append(f"Edge '{edge_name}' missing: {', '.join(miss)}")

    recalc_credits(char)
    if char.credits < 0:
        errors.append(
            f"Equipment exceeds starting credits (short by {abs(char.credits)} credits)."
        )

    return errors


class SaveRequest(BaseModel):
    character: dict
    save_json: bool = True
    save_html: bool = True
    save_txt: bool = True


def create_app() -> FastAPI:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="SW Savage Worlds Character Builder", version="1.0")

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        html_path = TEMPLATES_DIR / "builder.html"
        if not html_path.is_file():
            raise HTTPException(status_code=500, detail="Missing templates/builder.html")
        return html_path.read_text(encoding="utf-8")

    @app.get("/api/meta")
    async def api_meta() -> JSONResponse:
        species_list = [
            {
                "name": name,
                "abilities": data.get("abilities", ""),
                "notes": data.get("notes", ""),
            }
            for name, data in SPECIES.items()
        ]
        hindrance_list = [
            {"name": n, "pts": v.get("pts", 0), "desc": v.get("desc", "")}
            for n, v in sorted(HINDRANCES.items(), key=lambda x: x[0].lower())
        ]
        edge_list = [
            {
                "name": n,
                "requirements": v.get("requirements", ""),
                "desc": v.get("desc", ""),
            }
            for n, v in sorted(EDGES.items(), key=lambda x: x[0].lower())
        ]
        non_core = sorted(
            [s for s in SKILL_ATTRIBUTES if s not in set(CORE_SKILLS)],
            key=str.lower,
        )
        skill_order = non_core + list(CORE_SKILLS)

        # Omit career "desc" from meta; only benefits are used in the UI and on sheets.
        career_list = [
            {
                "name": n,
                "benefits": v.get("benefits", []) if isinstance(v, dict) else [],
            }
            for n, v in sorted(CAREERS.items(), key=lambda x: x[0].lower())
        ]

        return JSONResponse(
            {
                "attributes": ATTRIBUTES,
                "core_skills": CORE_SKILLS,
                "skill_attributes": SKILL_ATTRIBUTES,
                "skill_order": skill_order,
                "species": species_list,
                "careers": career_list,
                "hindrances": hindrance_list,
                "edges": edge_list,
                "weapons": [
                    {"name": n, "cost": v.get("cost", 0), "notes": v.get("notes", "")}
                    for n, v in _gear_entries_sorted_by_cost(WEAPONS)
                ],
                "armor": [
                    {"name": n, "cost": v.get("cost", 0), "toughness": v.get("toughness", "")}
                    for n, v in _gear_entries_sorted_by_cost(ARMOR)
                ],
                "gear": [
                    {"name": n, "cost": v.get("cost", 0)}
                    for n, v in _gear_entries_sorted_by_cost(GEAR)
                ],
            }
        )

    @app.post("/api/preview")
    async def api_preview(payload: dict) -> JSONResponse:
        char = hydrate_character(payload)
        errors = validate_character(char)
        data = char.to_dict()
        totals = compute_budget_totals(char)
        human_free_eligible = edges_meeting_trait_requirements(char)
        return JSONResponse(
            {
                "character": data,
                "errors": errors,
                "sheet_text": character_sheet_text(data),
                "totals": totals,
                "human_free_eligible_edges": human_free_eligible,
                "ok": len(errors) == 0,
            }
        )

    @app.post("/api/save")
    async def api_save(req: SaveRequest) -> JSONResponse:
        char = hydrate_character(req.character)
        errors = validate_character(char)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "Fix validation errors before saving.", "errors": errors},
            )
        data = char.to_dict()
        base = _safe_filename_base(char.name)
        written: list[str] = []

        if req.save_json:
            p = OUTPUT_DIR / f"{base}.json"
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
            written.append(str(p))

        if req.save_html:
            p = OUTPUT_DIR / f"{base}.html"
            p.write_text(character_sheet_html(data), encoding="utf-8")
            written.append(str(p))

        if req.save_txt:
            p = OUTPUT_DIR / f"{base}-sheet.txt"
            p.write_text(character_sheet_text(data), encoding="utf-8")
            written.append(str(p))

        if not written:
            raise HTTPException(status_code=400, detail="No export formats selected.")

        saved_items = [
            {
                "path": p,
                "filename": Path(p).name,
                "href": f"/api/download/{quote(Path(p).name)}",
            }
            for p in written
        ]
        return JSONResponse({"saved": written, "saved_items": saved_items, "character": data})

    @app.get("/api/download/{filename}")
    async def download(filename: str) -> FileResponse:
        """Serve a file from output/ by basename (URL-encoded names allowed, e.g. spaces)."""
        name = Path(unquote(filename)).name
        if not name:
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = (OUTPUT_DIR / name).resolve()
        out = OUTPUT_DIR.resolve()
        if path.parent != out:
            raise HTTPException(status_code=400, detail="Invalid path")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(path)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_api:app", host="127.0.0.1", port=8000, reload=False)
