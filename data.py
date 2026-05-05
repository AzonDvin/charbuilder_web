"""
Loads character data from JSON files.
All game data lives in JSON; this module provides the loader.
"""

import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, "data")


def _load_json(filename, default):
    """Load JSON file from data folder, return default if missing or invalid."""
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# Attributes & skills
_attrs = _load_json("attributes.json", {"attributes": [], "skill_attributes": {}, "core_skills": []})
ATTRIBUTES = _attrs.get("attributes", [])
SKILL_ATTRIBUTES = _attrs.get("skill_attributes", {})
CORE_SKILLS = _attrs.get("core_skills", [])

# Gear (weapons, armor, gear - filtered by category)
_all_gear = _load_json("gear.json", {})
WEAPONS = {k: v for k, v in _all_gear.items() if v.get("category") == "weapon"}
ARMOR = {k: v for k, v in _all_gear.items() if v.get("category") == "armor"}
GEAR = {k: v for k, v in _all_gear.items() if v.get("category") == "gear"}
ALL_GEAR = _all_gear

# Hindrances
HINDRANCES = _load_json("hindrances.json", {})

# Edges
EDGES = _load_json("edges.json", {})

# Species
SPECIES = _load_json("species.json", {})

# Careers (optional packages; no hindrance cost in this app)
CAREERS = _load_json("careers.json", {})
