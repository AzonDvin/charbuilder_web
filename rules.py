"""
Pure game-rule helpers used by the web app.
"""

from __future__ import annotations

import re

from character import Character, parse_species_granted_attribute_dice
from data import ARMOR, CAREERS, CORE_SKILLS, EDGES, GEAR, HINDRANCES, SKILL_ATTRIBUTES, WEAPONS


def die_to_num(die: str) -> int:
    return {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}.get(die, 4)


def num_to_die(num: int) -> str:
    return {4: "d4", 6: "d6", 8: "d8", 10: "d10", 12: "d12"}.get(num, "d4")


def get_base_credits(char: Character) -> int:
    """Starting credits from Hindrances and wealth Edges."""
    if "Poverty (Major)" in char.hindrances:
        return 125
    if "Poverty" in char.hindrances:
        return 250
    if "Filthy Rich" in char.edges:
        return 2500
    if "Rich" in char.edges:
        return 1500
    return 500


def recalc_credits(char: Character) -> None:
    """Set char.credits from base minus all purchases."""
    base = get_base_credits(char)
    weapon_cost = sum(WEAPONS.get(w, {}).get("cost", 0) for w in char.weapons)
    armor_cost = ARMOR.get(char.armor, {}).get("cost", 0)
    gear_cost = sum(GEAR.get(g, {}).get("cost", 0) for g in char.gear)
    char.credits = base - weapon_cost - armor_cost - gear_cost


def hindrance_name_from_listbox_line(line: str) -> str:
    """Parse hindrance key from listbox label like 'Name (1 pt)'."""
    if " pt)" in line:
        return line.rsplit(" (", 1)[0]
    return line


def edge_rank_from_requirements(requirements: str | None) -> str:
    """Infer rank from requirements text."""
    req = (requirements or "").lower()
    for rank in ["legendary", "heroic", "veteran", "seasoned", "novice"]:
        if rank in req:
            return rank.capitalize()
    return "Novice"


def edge_category_from_data(name: str, data: dict) -> str:
    """Infer an edge category for browsing/sorting."""
    n = (name or "").lower()
    desc = (data.get("desc", "") or "").lower()
    req = (data.get("requirements", "") or "").lower()
    blob = f"{n} {desc} {req}"

    if any(k in blob for k in ["force", "arcane", "power points", "miracle", "psionic"]):
        return "Power"
    if any(k in blob for k in ["command", "inspire", "battle", "allies"]):
        return "Leadership"
    if any(k in blob for k in ["persuasion", "contact", "connections", "streetwise"]):
        return "Social"
    if any(k in blob for k in ["investigation", "knowledge", "repair", "tracking", "survival", "scholar", "thief"]):
        return "Professional"
    if any(k in blob for k in ["shooting", "fighting", "parry", "shaken", "ranged", "attack", "weapon", "dodge"]):
        return "Combat"
    return "Background"


def edge_list_label(edge_name: str, edge_data: dict) -> str:
    cat = edge_category_from_data(edge_name, edge_data)
    rank = edge_rank_from_requirements(edge_data.get("requirements", ""))
    return f"{edge_name} [{cat} | {rank}]"


def edge_name_from_list_label(label: str) -> str:
    return label.split(" [", 1)[0]


def edge_missing_attribute_requirements(edge_data: dict, attributes: dict) -> list[str]:
    """Return unmet attribute requirements like ['Agility d8']."""
    req = edge_data.get("requirements", "") or ""
    missing: list[str] = []
    pattern = r"\b(Agility|Smarts|Spirit|Strength|Vigor)\s+d(4|6|8|10|12)\b"
    for attr, die in re.findall(pattern, req):
        needed = int(die)
        current = die_to_num(attributes.get(attr, "d4"))
        if current < needed:
            missing.append(f"{attr} d{needed}")
    return missing


def edge_missing_skill_requirements(
    edge_data: dict, skills: dict, skill_attributes: dict
) -> list[str]:
    """Return unmet skill requirements as readable clauses."""
    req = edge_data.get("requirements", "") or ""
    missing: list[str] = []
    all_skills = sorted(skill_attributes.keys(), key=len, reverse=True)
    clauses = [c.strip() for c in req.split(",") if c.strip()]
    die_pattern = re.compile(r"\bd(4|6|8|10|12)\b", re.IGNORECASE)

    for clause in clauses:
        die_match = die_pattern.search(clause)
        if not die_match:
            continue
        needed = int(die_match.group(1))
        clause_l = clause.lower()
        matched_skills = [s for s in all_skills if s.lower() in clause_l]
        if not matched_skills:
            continue

        def _skill_meets_requirement(skill_name: str) -> bool:
            current_val = skills.get(skill_name, "Untrained")
            if current_val == "Untrained":
                return False
            return die_to_num(current_val) >= needed

        if any(_skill_meets_requirement(s) for s in matched_skills):
            continue
        if len(matched_skills) == 1:
            missing.append(f"{matched_skills[0]} d{needed}")
        else:
            missing.append(f"{' or '.join(matched_skills)} d{needed}")
    return missing


def attribute_steps_spent(attributes: dict, attribute_names: list[str]) -> int:
    """Count die steps above d4 across all attributes (1 step = d4 -> d6, etc.)."""
    return sum((die_to_num(attributes.get(a, "d4")) - 4) // 2 for a in attribute_names)


def attribute_steps_billable(
    attributes: dict,
    attribute_names: list[str],
    species_abilities: str | None,
) -> int:
    """
    Die steps that count against the 5 free attribute steps (racial d6+ in an attribute
    is funded by the species text, not the player's 5 steps).
    """
    grants = parse_species_granted_attribute_dice(species_abilities)
    total = 0
    for a in attribute_names:
        cur_steps = (die_to_num(attributes.get(a, "d4")) - 4) // 2
        gift_steps = (die_to_num(grants.get(a, "d4")) - 4) // 2
        total += max(0, cur_steps - gift_steps)
    return total


def hindrance_points_on_attributes(attribute_steps: int) -> int:
    """Hindrance points consumed raising attributes beyond the 5 free steps (2 pts per extra step)."""
    return 2 * max(0, attribute_steps - 5)


def total_adjusted_skill_cost(
    skills: dict,
    attributes: dict,
    core_skills: list,
    skill_attributes: dict,
    species_abilities: str | None,
) -> int:
    """Sum of adjusted purchase costs for every skill in the skill list."""
    from character import adjusted_skill_purchase_cost

    core = set(core_skills)
    total = 0
    for skill_name in skill_attributes:
        die_value = skills.get(skill_name)
        if die_value is None:
            die_value = "d4" if skill_name in core else "Untrained"
        total += adjusted_skill_purchase_cost(
            skill_name,
            die_value,
            attributes,
            core,
            skill_attributes,
            species_abilities,
        )
    return total


def hindrance_points_after_skills(hindrance_after_attrs: int, skill_total_cost: int) -> int:
    """Hindrance pool remaining after skills."""
    skill_hindrance = max(0, skill_total_cost - 15)
    return max(0, hindrance_after_attrs - skill_hindrance)


def validate_hindrance_budget(
    hindrances: list[str],
    attribute_steps: int,
    skill_total_cost: int,
    edges: list[str],
    human_free_edges_used: list[str],
    species: str,
) -> tuple[list[str], int, int, int, int]:
    """
    Returns (errors, H_total, hindrance_on_attr, hindrance_after_attrs, hindrance_after_skills).

    hindrance_after_skills must cover 2 * paid_edges where paid_edges excludes human free list.
    """
    errors: list[str] = []
    unknown = [h for h in hindrances if h not in HINDRANCES]
    if unknown:
        errors.append(f"Unknown hindrance(s): {', '.join(unknown)}")

    H_total = sum(HINDRANCES[h]["pts"] for h in hindrances if h in HINDRANCES)
    if H_total > 4:
        errors.append(f"Hindrance points exceed 4 (currently {H_total}).")

    hindrance_on_attr = hindrance_points_on_attributes(attribute_steps)
    if hindrance_on_attr > H_total:
        errors.append(
            f"Attributes require {hindrance_on_attr} hindrance points beyond the 5 base "
            f"attribute steps, but only {H_total} hindrance points are available."
        )

    hindrance_after_attrs = H_total - hindrance_on_attr
    skill_hindrance = max(0, skill_total_cost - 15)
    if skill_hindrance > hindrance_after_attrs:
        errors.append(
            f"Skills need {skill_hindrance} hindrance points beyond the 15 base skill points, "
            f"but only {hindrance_after_attrs} hindrance points remain after attributes."
        )

    hindrance_after_skills = hindrance_points_after_skills(hindrance_after_attrs, skill_total_cost)

    known_edges = [e for e in edges if e in EDGES]
    paid_edges = [e for e in known_edges if e not in human_free_edges_used]
    edge_cost = 2 * len(paid_edges)
    if edge_cost > hindrance_after_skills:
        errors.append(
            f"Edges require {edge_cost} hindrance points (after skills), "
            f"but only {hindrance_after_skills} remain."
        )

    if species == "Human":
        if len(human_free_edges_used) > 1:
            errors.append("Humans may only use 1 free Edge.")
        for e in human_free_edges_used:
            if e not in edges:
                errors.append(f"Human free Edge '{e}' must also be listed in Edges.")
    elif human_free_edges_used:
        errors.append("Only Human characters may use human_free_edges_used.")

    return errors, H_total, hindrance_on_attr, hindrance_after_attrs, hindrance_after_skills


def suggest_skills_for_career(
    career_name: str,
    attributes: dict,
    species_abilities: str | None,
) -> dict[str, str] | None:
    """
    Return a suggested skill allocation that spends exactly the 15 base skill points
    (never touches hindrance points) weighted toward the career's priority skills.

    Returns a dict of {skill_name: die_value} for every skill that should have a
    value set, or None if the career has no suggested_skills list.

    Algorithm:
    - Core skills start at d4 (free).
    - Species skill grants are applied first at no cost.
    - Priority skills are raised in waves (→d6 first across all, then →d8, then →d10/d12)
      so no single skill hogs all the budget before others get a d6.
    - Any leftover budget fills secondary skills at d6, then raises core skills to d6.
    """
    from character import skill_purchase_cost, parse_species_granted_skill_dice

    career = CAREERS.get(career_name, {})
    priority: list[str] = career.get("suggested_skills", []) if isinstance(career, dict) else []
    if not priority:
        return None

    core = set(CORE_SKILLS)
    _die_n = {"Untrained": 0, "d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}
    _n_die = {0: "Untrained", 4: "d4", 6: "d6", 8: "d8", 10: "d10", 12: "d12"}

    # Initialise: core skills free at d4, everything else Untrained
    skills: dict[str, str] = {s: "d4" for s in core}

    # Apply species free skill grants first
    grants = parse_species_granted_skill_dice(species_abilities or "", SKILL_ATTRIBUTES.keys())
    for sk, g_die in grants.items():
        cur_n = _die_n.get(skills.get(sk, "Untrained"), 0)
        g_n = _die_n.get(g_die, 4)
        skills[sk] = _n_die[max(cur_n, g_n)]

    budget = 15  # base skill points only — never touch hindrance

    def _incr_cost(skill: str, from_die: str, to_die: str) -> int:
        """Marginal point cost to raise skill from from_die to to_die (one step)."""
        to_c = skill_purchase_cost(skill, to_die, attributes, core, SKILL_ATTRIBUTES)
        from_c = (
            0
            if from_die == "Untrained"
            else skill_purchase_cost(skill, from_die, attributes, core, SKILL_ATTRIBUTES)
        )
        return max(0, to_c - from_c)

    def _try_raise(skill: str, cap_die: str) -> bool:
        """
        Raise skill by exactly one die step toward cap_die if budget allows.
        Returns True if a raise happened.
        """
        nonlocal budget
        current = skills.get(skill, "Untrained")
        cur_n = _die_n.get(current, 0)
        cap_n = _die_n[cap_die]
        if cur_n >= cap_n:
            return False
        next_n = 4 if cur_n == 0 else cur_n + 2
        if next_n > cap_n:
            return False
        nd = _n_die[next_n]
        cost = _incr_cost(skill, current, nd)
        if cost <= budget:
            skills[skill] = nd
            budget -= cost
            return True
        return False

    # Phase A: raise each priority skill to d6, then d8 (in waves so early skills
    # don't starve later ones)
    for cap in ("d6", "d8"):
        cap_n = _die_n[cap]
        for skill in priority:
            cur_n = _die_n.get(skills.get(skill, "Untrained"), 0)
            while cur_n < cap_n and budget > 0:
                if _try_raise(skill, cap):
                    cur_n = _die_n.get(skills.get(skill, "Untrained"), 0)
                else:
                    break

    # Phase B: push priority skills further if budget remains
    for cap in ("d10", "d12"):
        cap_n = _die_n[cap]
        for skill in priority:
            cur_n = _die_n.get(skills.get(skill, "Untrained"), 0)
            while cur_n < cap_n and budget > 0:
                if _try_raise(skill, cap):
                    cur_n = _die_n.get(skills.get(skill, "Untrained"), 0)
                else:
                    break

    # Phase C: spend leftovers on secondary non-core skills at d6
    secondary = sorted(s for s in SKILL_ATTRIBUTES if s not in priority and s not in core)
    for skill in secondary:
        if budget <= 0:
            break
        if skills.get(skill, "Untrained") == "Untrained":
            cost = _incr_cost(skill, "Untrained", "d6")
            if cost <= budget:
                skills[skill] = "d6"
                budget -= cost

    # Phase D: raise any core skills not in priority to d6 with remaining budget
    for skill in CORE_SKILLS:
        if budget <= 0:
            break
        if skill not in priority:
            cost = _incr_cost(skill, skills.get(skill, "d4"), "d6")
            if cost <= budget:
                skills[skill] = "d6"
                budget -= cost

    return skills
