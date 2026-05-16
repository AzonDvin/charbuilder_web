"""
Character model for Savage Worlds Star Wars.
"""

import re
from typing import Iterable

try:
    from data import ARMOR
except ImportError:
    ARMOR = {}


def _die_to_num(die: str) -> int:
    return {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}.get(die, 4)


def _num_to_die(num: int) -> str:
    return {4: "d4", 6: "d6", 8: "d8", 10: "d10", 12: "d12"}.get(num, "d4")


def parse_species_granted_skill_dice(
    abilities: str | None, valid_skill_names: Iterable[str]
) -> dict[str, str]:
    """
    Find explicit racial skill dice in species text, e.g. 'Piloting d6', 'Common Knowledge d6'.

    Only matches names in valid_skill_names (longest first). Ignores attribute lines
    like 'd6 Strength' / 'd6 Smarts'.
    """
    if not abilities:
        return {}
    text = abilities.strip()
    text = re.sub(
        r"\b(d4|d6|d8|d10|d12)\s+(Agility|Smarts|Spirit|Strength|Vigor)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    names = sorted(set(valid_skill_names), key=len, reverse=True)
    out: dict[str, str] = {}
    for name in names:
        pat = (
            r"(?<![A-Za-z])"
            + re.escape(name)
            + r"\s+d(4|6|8|10|12)\b"
        )
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            die = f"d{m.group(1)}"
            if name not in out or _die_to_num(die) > _die_to_num(out[name]):
                out[name] = die
    return out


def parse_species_granted_attribute_dice(abilities: str | None) -> dict[str, str]:
    """
    Racial minimum dice written as 'd6 Strength', 'd8 Smarts' (die before attribute name).

    Used to merge starting attributes and to exclude those steps from the attribute
    creation budget (same wording as species.json entries like Wookiee / Chiss).
    """
    if not abilities:
        return {}
    pattern = re.compile(
        r"\b(d4|d6|d8|d10|d12)\s+(Agility|Smarts|Spirit|Strength|Vigor)\b",
        re.IGNORECASE,
    )
    out: dict[str, str] = {}
    for m in pattern.finditer(abilities.strip()):
        die = m.group(1).lower()
        if not die.startswith("d"):
            die = f"d{die}"
        raw = m.group(2)
        attr = raw[0].upper() + raw[1:].lower()
        if attr not in {"Agility", "Smarts", "Spirit", "Strength", "Vigor"}:
            continue
        prev = out.get(attr, "d4")
        out[attr] = _num_to_die(max(_die_to_num(prev), _die_to_num(die)))
    return out


def skill_purchase_cost(
    skill_name: str,
    die_value: str,
    attributes: dict,
    core_skills: set,
    skill_attributes: dict,
) -> int:
    """Savage Worlds-style skill point cost from default (core d4 / non-core Untrained) to die_value."""
    is_core = skill_name in core_skills
    if die_value == "Untrained":
        return 0
    if die_value == "d4":
        return 0 if is_core else 1
    if die_value not in {"d6", "d8", "d10", "d12"}:
        return 0
    linked = skill_attributes.get(skill_name, "Smarts")
    attr_val = _die_to_num(attributes.get(linked, "d4"))
    val = _die_to_num(die_value)
    total = 0 if is_core else 1
    for step in range(1, (val - 4) // 2 + 1):
        current_die = 4 + (step - 1) * 2
        total += 1 if current_die < attr_val else 2
    return total


def adjusted_skill_purchase_cost(
    skill_name: str,
    die_value: str,
    attributes: dict,
    core_skills: set,
    skill_attributes: dict,
    species_abilities: str | None,
) -> int:
    """Purchase cost with species 'Skill d6' grants treated as already paid up to that die."""
    raw = skill_purchase_cost(
        skill_name, die_value, attributes, core_skills, skill_attributes
    )
    grants = parse_species_granted_skill_dice(
        species_abilities, skill_attributes.keys()
    )
    grant_die = grants.get(skill_name)
    if not grant_die:
        return raw
    raw_grant = skill_purchase_cost(
        skill_name, grant_die, attributes, core_skills, skill_attributes
    )
    return max(0, raw - raw_grant)


def size_toughness_bonus_from_species_abilities(text: str | None) -> int:
    """+N Size in species abilities adds +N Toughness (Savage Worlds Deluxe Size/mass rule)."""
    if not text:
        return 0
    total = 0
    for m in re.finditer(r"\+(\d+)\s*Size", text, re.IGNORECASE):
        total += int(m.group(1))
    return total


def compute_display_toughness(
    attributes: dict,
    armor_name: str,
    species_abilities: str | None = None,
) -> int:
    """2 + half Vigor + armor Toughness bonus + species Size bonus."""
    attrs = attributes or {}
    vig = attrs.get("Vigor", "d4")
    mapping = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}
    vigor_val = mapping.get(vig, 4)
    base = 2 + (vigor_val // 2)
    armor_bonus = 0
    if armor_name and armor_name in ARMOR:
        t = ARMOR[armor_name].get("toughness", "0")
        if "+" in str(t):
            try:
                armor_bonus = int(str(t).replace("+", ""))
            except ValueError:
                pass
    size_bonus = size_toughness_bonus_from_species_abilities(species_abilities)
    return base + armor_bonus + size_bonus


class Character:
    """Represents a Savage Worlds Star Wars character."""

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """Build a Character from an export / API payload (partial keys allowed)."""
        c = cls()
        if not data:
            return c
        c.name = str(data.get("name") or "")
        c.species = str(data.get("species") or "")
        c.species_abilities = str(data.get("species_abilities") or "")
        attrs = data.get("attributes")
        if isinstance(attrs, dict):
            for k, v in attrs.items():
                if k in c.attributes and isinstance(v, str):
                    c.attributes[k] = v
        skills = data.get("skills")
        if isinstance(skills, dict):
            c.skills = {str(k): str(v) for k, v in skills.items()}
        hind = data.get("hindrances")
        if isinstance(hind, list):
            c.hindrances = [str(h) for h in hind]
        edges = data.get("edges")
        if isinstance(edges, list):
            c.edges = [str(e) for e in edges]
        weapons = data.get("weapons")
        if isinstance(weapons, list):
            c.weapons = [str(w) for w in weapons]
        if "armor" in data:
            raw = data["armor"]
            c.armor = "" if raw is None else str(raw)
        if c.armor == "No Armor":
            c.armor = ""
        gear = data.get("gear")
        if isinstance(gear, list):
            c.gear = [str(g) for g in gear]
        hf = data.get("human_free_edges_used")
        if isinstance(hf, list):
            c.human_free_edges_used = [str(x) for x in hf]
        c.career = str(data.get("career") or "")
        return c

    def __init__(self):
        self.name = ""
        self.species = ""
        self.species_abilities = ""
        self.attributes = {
            "Agility": "d4",
            "Smarts": "d4",
            "Spirit": "d4",
            "Strength": "d4",
            "Vigor": "d4",
        }
        self.skills = {}
        self.hindrances = []
        self.edges = []
        self.weapons = []
        self.armor = ""
        self.gear = []
        self.credits = 500
        self.hindrance_points_remaining = 0
        self.skill_points_remaining = 15
        self.human_free_edges_used = []  # Edges taken with Human species bonus
        self.career = ""

    def get_toughness(self):
        """Calculate toughness (2 + half Vigor + armor + species Size bonus)."""
        return compute_display_toughness(
            self.attributes,
            self.armor,
            self.species_abilities,
        )

    def _die_to_num(self, die):
        """Convert d4/d6/d8/d10/d12 to numeric value."""
        mapping = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12}
        return mapping.get(die, 4)

    def get_parry(self):
        """Calculate Parry (2 + half Fighting)."""
        fighting = self.skills.get("Fighting", "d4")
        val = self._die_to_num(fighting)
        return 2 + (val // 2)

    def to_dict(self):
        """Export character as dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "species_abilities": self.species_abilities,
            "attributes": self.attributes.copy(),
            "skills": self.skills.copy(),
            "hindrances": self.hindrances.copy(),
            "edges": self.edges.copy(),
            "weapons": self.weapons.copy(),
            "armor": self.armor,
            "gear": self.gear.copy(),
            "credits": self.credits,
            "toughness": self.get_toughness(),
            "parry": self.get_parry(),
            "human_free_edges_used": getattr(self, "human_free_edges_used", []),
            "career": getattr(self, "career", ""),
        }


def merge_species_attribute_minimums(char: Character) -> None:
    """Raise each attribute to at least the species minimum (e.g. d6 Strength for Wookiee)."""
    grants = parse_species_granted_attribute_dice(char.species_abilities)
    for attr, g_die in grants.items():
        if attr not in char.attributes:
            continue
        cur = char.attributes.get(attr, "d4")
        char.attributes[attr] = _num_to_die(max(_die_to_num(cur), _die_to_num(g_die)))
