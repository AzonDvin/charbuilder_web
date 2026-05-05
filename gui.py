#!/usr/bin/env python3
"""
Savage Worlds Star Wars Character Builder - GUI
A step-by-step wizard for creating characters.
"""

import json
import re
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog, scrolledtext

from character import (
    Character,
    adjusted_skill_purchase_cost,
    merge_species_attribute_minimums,
    parse_species_granted_attribute_dice,
    parse_species_granted_skill_dice,
)
from character_sheet import character_sheet_html, character_sheet_text
from data import (
    ATTRIBUTES,
    SKILL_ATTRIBUTES,
    CORE_SKILLS,
    WEAPONS,
    ARMOR,
    CAREERS,
    GEAR,
    ALL_GEAR,
    HINDRANCES,
    EDGES,
    SPECIES,
)
from rules import (
    attribute_steps_billable,
    die_to_num,
    num_to_die,
    get_base_credits,
    recalc_credits,
    hindrance_name_from_listbox_line,
    edge_rank_from_requirements,
    edge_category_from_data,
    edge_list_label,
    edge_name_from_list_label,
    edge_missing_attribute_requirements,
    edge_missing_skill_requirements as _edge_missing_skill_requirements_impl,
)


def _hindrance_name_from_listbox_line(line):
    return hindrance_name_from_listbox_line(line)


def _edge_rank_from_requirements(requirements):
    return edge_rank_from_requirements(requirements)


def _edge_category_from_data(name, data):
    return edge_category_from_data(name, data)


def _edge_list_label(edge_name, edge_data):
    return edge_list_label(edge_name, edge_data)


def _edge_name_from_list_label(label):
    return edge_name_from_list_label(label)


def _edge_missing_attribute_requirements(edge_data, attributes):
    return edge_missing_attribute_requirements(edge_data, attributes)


def _edge_missing_skill_requirements(edge_data, skills):
    return _edge_missing_skill_requirements_impl(edge_data, skills, SKILL_ATTRIBUTES)


def _character_filename(char):
    """Get a safe filename from the character name."""
    name = (char.name or "character").strip()
    if not name:
        name = "character"
    # Remove invalid filename characters
    for c in '\\/:*?"<>|':
        name = name.replace(c, "_")
    return f"{name}.json"


def format_item_details(name, data):
    """Format equipment details for display. data can be from WEAPONS, ARMOR, or GEAR."""
    if not data:
        return ""
    lines = [f"** {name} **", f"Cost: {data.get('cost', 0)} credits", ""]
    if "damage" in data:
        lines.append(f"Damage: {data['damage']}")
    if "range" in data:
        lines.append(f"Range: {data['range']}")
    if "toughness" in data:
        t = data["toughness"]
        lines.append(f"Toughness: +{t}" if t and str(t) != "0" else "Toughness: +0")
    if data.get("notes"):
        lines.append(f"Game effect: {data['notes']}")
    if data.get("desc"):
        lines.extend(["", data["desc"]])
    return "\n".join(lines)


def _hindrance_name_from_listbox_line(line):
    """Parse hindrance key from listbox label like 'Name (1 pt)' or 'Habit (Major) (2 pt)'."""
    if " pt)" in line:
        return line.rsplit(" (", 1)[0]
    return line


def format_hindrance_details(name, data):
    """Format hindrance type, points, and description for the details panel."""
    if not data:
        return ""
    lines = [
        f"** {name} **",
        f"Type: {data.get('type', '?')}  |  Hindrance points: {data.get('pts', 0)}",
        "",
        "Effect:",
        data.get("desc", "No description."),
    ]
    return "\n".join(lines)


def format_edge_details(name, data):
    """Format edge requirements and effect for the details panel."""
    if not data:
        return ""
    lines = [
        f"** {name} **",
        f"Requirements: {data.get('requirements', 'None') or 'None'}",
        "",
        "Effect:",
        data.get("desc", "No description."),
    ]
    return "\n".join(lines)


def _edge_rank_from_requirements(requirements):
    """Infer rank from requirements text."""
    req = (requirements or "").lower()
    for rank in ["legendary", "heroic", "veteran", "seasoned", "novice"]:
        if rank in req:
            return rank.capitalize()
    return "Novice"


def _edge_category_from_data(name, data):
    """Infer an edge category for browsing/sorting."""
    n = (name or "").lower()
    desc = (data.get("desc", "") or "").lower()
    req = (data.get("requirements", "") or "").lower()
    blob = f"{n} {desc} {req}"

    if any(k in blob for k in ["force", "arcane", "power points", "miracle", "psionic"]):
        return "Power"
    if any(k in blob for k in ["command", "inspire", "battle", "allies"]):
        return "Leadership"
    if any(k in blob for k in ["charisma", "persuasion", "contact", "connections", "streetwise"]):
        return "Social"
    if any(k in blob for k in ["investigation", "knowledge", "repair", "tracking", "survival", "scholar", "thief"]):
        return "Professional"
    if any(k in blob for k in ["shooting", "fighting", "parry", "shaken", "ranged", "attack", "weapon", "dodge"]):
        return "Combat"
    return "Background"


def _edge_list_label(edge_name, edge_data):
    cat = _edge_category_from_data(edge_name, edge_data)
    rank = _edge_rank_from_requirements(edge_data.get("requirements", ""))
    return f"{edge_name} [{cat} | {rank}]"


def _edge_name_from_list_label(label):
    return label.split(" [", 1)[0]


def _edge_missing_attribute_requirements(edge_data, attributes):
    """Return unmet attribute requirements like ['Agility d8']."""
    req = edge_data.get("requirements", "") or ""
    missing = []
    pattern = r"\b(Agility|Smarts|Spirit|Strength|Vigor)\s+d(4|6|8|10|12)\b"
    for attr, die in re.findall(pattern, req):
        needed = int(die)
        current = die_to_num(attributes.get(attr, "d4"))
        if current < needed:
            missing.append(f"{attr} d{needed}")
    return missing


def _edge_missing_skill_requirements(edge_data, skills):
    """Return unmet skill requirements as readable clauses."""
    req = edge_data.get("requirements", "") or ""
    missing = []
    all_skills = sorted(SKILL_ATTRIBUTES.keys(), key=len, reverse=True)
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
        # If multiple skills are mentioned in one clause, treat as OR.
        def _skill_meets_requirement(skill_name):
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


class CharacterBuilderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Savage Worlds Star Wars - Character Builder")
        self.root.geometry("1100x850")
        self.root.minsize(980, 760)
        self.ui_font_family = self._pick_starwars_font_family()

        self.char = Character()
        self.current_step = 0
        self.steps = [
            ("Concept & Species", self.step_concept),
            ("Hindrances", self.step_hindrances),
            ("Attributes", self.step_attributes),
            ("Skills", self.step_skills),
            ("Edges", self.step_edges),
            ("Weapons, Armor & Gear", self.step_armor_gear),
            ("Summary", self.step_summary),
        ]

        self._setup_ui()

    def _setup_ui(self):
        """Create main window layout."""
        # Header
        header = tk.Frame(self.root, bg="#1a1a2e", padx=15, pady=10)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="SAVAGE WORLDS STAR WARS",
            font=("Segoe UI", 18, "bold"),
            bg="#1a1a2e",
            fg="#8ec5ff",
        ).pack()
        tk.Label(
            header,
            text="Character Builder",
            font=("Segoe UI", 12),
            bg="#1a1a2e",
            fg="#a2a2a2",
        ).pack()

        # Step indicator
        self.step_label = tk.Label(
            self.root,
            text=f"Step 1 of {len(self.steps)}: {self.steps[0][0]}",
            font=("Segoe UI", 11, "bold"),
        )
        self.step_label.pack(pady=(10, 5))

        # Content frame (where step content goes)
        self.content_frame = tk.Frame(self.root, padx=20, pady=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Navigation buttons
        nav_frame = tk.Frame(self.root, pady=15)
        nav_frame.pack(fill=tk.X)

        self.btn_back = tk.Button(
            nav_frame,
            text="← Back",
            font=("Segoe UI", 10),
            command=self._go_back,
            state=tk.DISABLED,
            width=10,
        )
        self.btn_back.pack(side=tk.LEFT, padx=10)

        self.btn_next = tk.Button(
            nav_frame,
            text="Next →",
            font=("Segoe UI", 10),
            command=self._go_next,
            width=10,
        )
        self.btn_next.pack(side=tk.RIGHT, padx=10)

        self._show_step(0)
        self._apply_starwars_font_theme(self.root)

    def _pick_starwars_font_family(self):
        """Pick a Star Wars-like TrueType font with safe fallbacks."""
        available = {f.lower(): f for f in tkfont.families(self.root)}
        candidates = [
            "Orbitron",          # Sci-fi style if user installed it
            "BankGothic Md BT",  # angular display font common on Windows installs
            "Agency FB",         # condensed futuristic fallback
            "Bahnschrift",       # modern TrueType Windows default
            "Segoe UI",          # guaranteed fallback
        ]
        for name in candidates:
            if name.lower() in available:
                return available[name.lower()]
                
        return "Segoe UI"

    def _apply_starwars_font_theme(self, widget):
        """Replace Segoe UI widgets with chosen themed family."""
        try:
            if "font" in widget.keys():
                f = tkfont.Font(font=widget.cget("font"))
                actual = f.actual()
                if actual.get("family") == "Segoe UI":
                    size = actual.get("size", 10)
                    styles = []
                    if actual.get("weight") == "bold":
                        styles.append("bold")
                    if actual.get("slant") == "italic":
                        styles.append("italic")
                    widget.configure(font=(self.ui_font_family, size, *styles))
        except Exception:
            pass
        for child in widget.winfo_children():
            self._apply_starwars_font_theme(child)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _show_step(self, step_index):
        self.current_step = step_index
        self._clear_content()
        self.steps[step_index][1]()
        self._apply_starwars_font_theme(self.content_frame)
        self.step_label.config(
            text=f"Step {step_index + 1} of {len(self.steps)}: {self.steps[step_index][0]}"
        )
        self.btn_back.config(state=tk.NORMAL if step_index > 0 else tk.DISABLED)
        if step_index == len(self.steps) - 1:
            self.btn_next.config(text="Save & Finish")
        else:
            self.btn_next.config(text="Next →")

    def _go_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _go_next(self):
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
        else:
            self.root.quit()

    def step_concept(self):
        tk.Label(
            self.content_frame,
            text="Think about who your character is:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Smuggler? Jedi? Soldier? Scoundrel?",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Character Name",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(15, 5))
        self.name_var = tk.StringVar(value=self.char.name)
        tk.Entry(
            self.content_frame,
            textvariable=self.name_var,
            font=("Segoe UI", 12),
            width=40,
        ).pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            self.content_frame,
            text="Choose your character's species:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(15, 8))

        self.species_var = tk.StringVar(value=self.char.species or "Human")
        species_list = list(SPECIES.keys())
        cb = ttk.Combobox(
            self.content_frame,
            textvariable=self.species_var,
            values=species_list,
            state="readonly",
            font=("Segoe UI", 11),
            width=25,
        )
        cb.pack(fill=tk.X, pady=5)
        if species_list:
            cb.set(species_list[0] if not self.char.species else self.char.species)

        self.species_info = tk.Label(
            self.content_frame,
            text="",
            font=("Segoe UI", 9),
            fg="gray",
            wraplength=700,
            justify=tk.LEFT,
        )
        self.species_info.pack(anchor=tk.W, pady=(8, 0))

        def update_info(*args):
            sp = self.species_var.get()
            if sp and sp in SPECIES:
                s = SPECIES[sp]
                self.species_info.config(
                    text=f"{s['abilities']}\n{s.get('notes', '')}"
                )

        self.species_var.trace_add("write", update_info)
        update_info()

        tk.Label(
            self.content_frame,
            text="Choose a career:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(15, 8))

        career_values = [""] + sorted(CAREERS.keys(), key=str.lower)
        self.career_var = tk.StringVar(
            value=(self.char.career if getattr(self.char, "career", "") in CAREERS else "")
        )
        cb_career = ttk.Combobox(
            self.content_frame,
            textvariable=self.career_var,
            values=career_values,
            state="readonly",
            font=("Segoe UI", 11),
            width=25,
        )
        cb_career.pack(fill=tk.X, pady=5)
        if getattr(self.char, "career", "") in CAREERS:
            cb_career.set(self.char.career)
        else:
            cb_career.set("")

        self.career_info = tk.Label(
            self.content_frame,
            text="",
            font=("Segoe UI", 9),
            fg="gray",
            wraplength=700,
            justify=tk.LEFT,
        )
        self.career_info.pack(anchor=tk.W, pady=(8, 0))

        def update_career_info(*args):
            cr = self.career_var.get()
            if not cr or cr not in CAREERS:
                self.career_info.config(text="")
                return
            data = CAREERS[cr]
            bits = []
            desc = (data.get("desc") or "").strip()
            if desc:
                bits.append(desc)
            for b in data.get("benefits") or []:
                if not isinstance(b, dict):
                    continue
                title = (b.get("title") or "").strip()
                eff = (b.get("effect") or "").strip()
                typ = (b.get("type") or "").strip()
                tag = f" [{typ}]" if typ else ""
                if title and eff:
                    bits.append(f"• {title}{tag}: {eff}")
                elif title:
                    bits.append(f"• {title}{tag}")
                elif eff:
                    bits.append(f"• {eff}")
            self.career_info.config(text="\n\n".join(bits))

        self.career_var.trace_add("write", update_career_info)
        update_career_info()

        def save():
            self.char.name = self.name_var.get().strip()
            self.char.species = self.species_var.get()
            self.char.species_abilities = SPECIES.get(
                self.char.species, {}
            ).get("abilities", "")
            self.char.career = self.career_var.get().strip()

        self._save_step = save

    def step_species(self):
        tk.Label(
            self.content_frame,
            text="Choose your character's species:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.species_var = tk.StringVar(value=self.char.species or "Human")
        species_list = list(SPECIES.keys())
        cb = ttk.Combobox(
            self.content_frame,
            textvariable=self.species_var,
            values=species_list,
            state="readonly",
            font=("Segoe UI", 11),
            width=25,
        )
        cb.pack(fill=tk.X, pady=5)
        if species_list:
            cb.set(species_list[0] if not self.char.species else self.char.species)

        self.species_info = tk.Label(
            self.content_frame,
            text="",
            font=("Segoe UI", 9),
            fg="gray",
            wraplength=500,
            justify=tk.LEFT,
        )
        self.species_info.pack(anchor=tk.W, pady=15)

        def update_info(*args):
            sp = self.species_var.get()
            if sp and sp in SPECIES:
                s = SPECIES[sp]
                self.species_info.config(
                    text=f"{s['abilities']}\n{s.get('notes', '')}"
                )

        self.species_var.trace_add("write", update_info)
        update_info()

        def save():
            self.char.species = self.species_var.get()
            self.char.species_abilities = SPECIES.get(
                self.char.species, {}
            ).get("abilities", "")

        self._save_step = save

    def step_hindrances(self):
        tk.Label(
            self.content_frame,
            text="Take hindrances for extra attribute points, skills, or edges.",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Maximum 4 points (1 Major = 2 pts, 1 Minor = 1 pt)",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        pts_frame = tk.Frame(self.content_frame)
        pts_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(pts_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="Available", font=("Segoe UI", 9, "bold")).pack()
        self.hindrance_available = tk.Listbox(list_frame, height=12, font=("Segoe UI", 10))
        self.hindrance_available.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll1 = ttk.Scrollbar(list_frame, command=self.hindrance_available.yview)
        scroll1.pack(side=tk.LEFT, fill=tk.Y)
        self.hindrance_available.config(yscrollcommand=scroll1.set)

        for h, v in HINDRANCES.items():
            self.hindrance_available.insert(tk.END, f"{h} ({v['pts']} pt)")

        btn_frame = tk.Frame(pts_frame)
        btn_frame.pack(side=tk.LEFT, padx=10)

        def add_hindrance():
            sel = self.hindrance_available.curselection()
            if not sel:
                return
            idx = sel[0]
            item = self.hindrance_available.get(idx)
            name = _hindrance_name_from_listbox_line(item)
            pts = HINDRANCES[name]["pts"]
            current_pts = sum(
                HINDRANCES[h]["pts"] for h in self.char.hindrances
            )
            if current_pts + pts > 4:
                messagebox.showwarning(
                    "Too many points",
                    f"That would exceed 4 points. You have {4 - current_pts} left.",
                )
                return
            self.char.hindrances.append(name)
            self.hindrance_available.delete(idx)
            self.hindrance_chosen.insert(tk.END, item)
            self.char.hindrance_points_remaining = current_pts + pts
            self.hindrance_pts_label.config(
                text=f"Points: {self.char.hindrance_points_remaining}"
            )

        def remove_hindrance():
            sel = self.hindrance_chosen.curselection()
            if not sel:
                return
            idx = sel[0]
            item = self.hindrance_chosen.get(idx)
            name = _hindrance_name_from_listbox_line(item)
            pts = HINDRANCES[name]["pts"]
            self.char.hindrances.remove(name)
            self.hindrance_chosen.delete(idx)
            self.hindrance_available.insert(tk.END, item)
            current_pts = sum(HINDRANCES[h]["pts"] for h in self.char.hindrances)
            self.char.hindrance_points_remaining = current_pts
            self.hindrance_pts_label.config(
                text=f"Points: {self.char.hindrance_points_remaining}"
            )

        tk.Button(btn_frame, text="Add →", command=add_hindrance, width=8).pack(
            pady=5
        )
        tk.Button(btn_frame, text="← Remove", command=remove_hindrance, width=8).pack(
            pady=5
        )

        chosen_frame = tk.Frame(pts_frame)
        chosen_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(chosen_frame, text="Chosen", font=("Segoe UI", 9, "bold")).pack()
        self.hindrance_chosen = tk.Listbox(chosen_frame, height=12, font=("Segoe UI", 10))
        self.hindrance_chosen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll2 = ttk.Scrollbar(chosen_frame, command=self.hindrance_chosen.yview)
        scroll2.pack(side=tk.LEFT, fill=tk.Y)
        self.hindrance_chosen.config(yscrollcommand=scroll2.set)

        self.hindrance_available.delete(0, tk.END)
        for h, v in HINDRANCES.items():
            if h not in self.char.hindrances:
                self.hindrance_available.insert(tk.END, f"{h} ({v['pts']} pt)")
        for h in self.char.hindrances:
            self.hindrance_chosen.insert(tk.END, f"{h} ({HINDRANCES[h]['pts']} pt)")

        tk.Label(
            self.content_frame,
            text="Click a hindrance in either list to see its effect.",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(8, 4))

        hindrance_details_txt = scrolledtext.ScrolledText(
            self.content_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            height=6,
            state=tk.DISABLED,
        )
        hindrance_details_txt.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        def show_hindrance_details(evt):
            w = evt.widget
            sel = w.curselection()
            if not sel:
                return
            item = w.get(sel[0])
            name = _hindrance_name_from_listbox_line(item)
            detail = format_hindrance_details(name, HINDRANCES.get(name, {}))
            hindrance_details_txt.config(state=tk.NORMAL)
            hindrance_details_txt.delete("1.0", tk.END)
            hindrance_details_txt.insert("1.0", detail)
            hindrance_details_txt.config(state=tk.DISABLED)

        self.hindrance_available.bind("<<ListboxSelect>>", show_hindrance_details)
        self.hindrance_chosen.bind("<<ListboxSelect>>", show_hindrance_details)

        self.char.hindrance_points_remaining = sum(
            HINDRANCES[h]["pts"] for h in self.char.hindrances
        )
        self.hindrance_pts_label = tk.Label(
            self.content_frame,
            text=f"Points: {self.char.hindrance_points_remaining}",
            font=("Segoe UI", 10, "bold"),
        )
        self.hindrance_pts_label.pack(pady=10)

        self._save_step = lambda: None

    def step_attributes(self):
        merge_species_attribute_minimums(self.char)
        self._species_attr_floor = parse_species_granted_attribute_dice(
            self.char.species_abilities
        )

        tk.Label(
            self.content_frame,
            text="Each attribute starts at d4. Spend 5 points (1 pt = 1 die step).",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W)
        if self._species_attr_floor:
            grant_txt = ", ".join(
                f"{a} {d}" for a, d in sorted(self._species_attr_floor.items())
            )
            tk.Label(
                self.content_frame,
                text=(
                    f"Species attribute minimums (already set; don't count vs. your 5 steps): "
                    f"{grant_txt}"
                ),
                font=("Segoe UI", 9),
                fg="gray",
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(0, 6))
        if self.char.hindrance_points_remaining >= 2:
            tk.Label(
                self.content_frame,
                text=f"Bonus: {self.char.hindrance_points_remaining} hindrance pts (2 pts = +1 attribute)",
                font=("Segoe UI", 9),
                fg="green",
            ).pack(anchor=tk.W, pady=(0, 10))

        self.attr_vars = {}
        # Steps that count against the 5 free attribute steps (species d6+ is excluded)
        spent_base = attribute_steps_billable(
            self.char.attributes, ATTRIBUTES, self.char.species_abilities
        )
        self.attr_points_remaining = max(0, 5 - spent_base)
        self.attr_hindrance_remaining = self.char.hindrance_points_remaining

        attr_frame = tk.Frame(self.content_frame)
        attr_frame.pack(fill=tk.X, pady=10)

        for attr in ATTRIBUTES:
            row = tk.Frame(attr_frame)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=attr, width=12, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value=self.char.attributes.get(attr, "d4"))
            self.attr_vars[attr] = var
            opt = ttk.Combobox(
                row,
                textvariable=var,
                values=["d4", "d6", "d8", "d10", "d12"],
                state="readonly",
                width=6,
            )
            opt.pack(side=tk.LEFT, padx=5)

            def make_up(att):
                def up():
                    v = self.attr_vars[att].get()
                    n = die_to_num(v)
                    if n < 12 and self.attr_points_remaining > 0:
                        self.attr_vars[att].set(num_to_die(n + 2))
                        self.attr_points_remaining -= 1
                        self.attr_pts_label.config(
                            text=f"Base points: {self.attr_points_remaining} | Hindrance pts: {self.attr_hindrance_remaining}"
                        )
                    elif n < 12 and self.attr_hindrance_remaining >= 2:
                        self.attr_vars[att].set(num_to_die(n + 2))
                        self.attr_hindrance_remaining -= 2
                        self.char.hindrance_points_remaining = self.attr_hindrance_remaining
                        self.attr_pts_label.config(
                            text=f"Base points: {self.attr_points_remaining} | Hindrance pts: {self.attr_hindrance_remaining}"
                        )

                return up

            def make_down(att):
                def down():
                    v = self.attr_vars[att].get()
                    n = die_to_num(v)
                    floor_n = die_to_num(self._species_attr_floor.get(att, "d4"))
                    if n <= 4:
                        return
                    next_n = n - 2
                    if next_n < floor_n:
                        return
                    self.attr_vars[att].set(num_to_die(next_n))
                    self.attr_points_remaining += 1
                    self.attr_pts_label.config(
                        text=f"Base points: {self.attr_points_remaining} | Hindrance pts: {self.attr_hindrance_remaining}"
                    )

                return down

            tk.Button(row, text="+", command=make_up(attr), width=3).pack(
                side=tk.LEFT, padx=2
            )
            tk.Button(row, text="-", command=make_down(attr), width=3).pack(
                side=tk.LEFT
            )

        self.attr_pts_label = tk.Label(
            self.content_frame,
            text=f"Base points: {self.attr_points_remaining} | Hindrance pts: {self.attr_hindrance_remaining}",
            font=("Segoe UI", 10),
        )
        self.attr_pts_label.pack(pady=10)

        # Apply any existing attributes
        for attr in ATTRIBUTES:
            self.attr_vars[attr].set(self.char.attributes.get(attr, "d4"))

        def save():
            for attr in ATTRIBUTES:
                self.char.attributes[attr] = self.attr_vars[attr].get()
            self.char.hindrance_points_remaining = self.attr_hindrance_remaining

        self._save_step = save

    def _skill_cost(self, skill_name, die_value):
        """Calculate cost for a skill at given die level (species Skill dN grants are free)."""
        core = set(CORE_SKILLS)
        return adjusted_skill_purchase_cost(
            skill_name,
            die_value,
            self.char.attributes,
            core,
            SKILL_ATTRIBUTES,
            self.char.species_abilities,
        )

    def _recalc_skill_pts(self):
        total_pts = 15 + self.char.hindrance_points_remaining
        used = sum(
            self._skill_cost(sk, var.get())
            for sk, var in getattr(self, "skill_vars", {}).items()
        )
        self.skill_pts_remaining = total_pts - used
        if hasattr(self, "skill_pts_label") and self.skill_pts_label.winfo_exists():
            self.skill_pts_label.config(
                text=f"Skill points remaining: {self.skill_pts_remaining}"
            )

    def step_skills(self):
        core_skills = set(CORE_SKILLS)
        for s in CORE_SKILLS:
            if s not in self.char.skills:
                self.char.skills[s] = "d4"

        self._species_skill_grants = parse_species_granted_skill_dice(
            self.char.species_abilities, SKILL_ATTRIBUTES.keys()
        )
        for sk, g_die in self._species_skill_grants.items():
            cur = self.char.skills.get(
                sk, "Untrained" if sk not in core_skills else "d4"
            )
            if cur == "Untrained":
                self.char.skills[sk] = g_die
            else:
                self.char.skills[sk] = num_to_die(
                    max(die_to_num(cur), die_to_num(g_die))
                )

        total_pts = 15 + self.char.hindrance_points_remaining
        tk.Label(
            self.content_frame,
            text=f"15 base + {self.char.hindrance_points_remaining} hindrance = {total_pts} skill points.",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="1 pt/step up to linked attr, 2 pts/step above.",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(0, 10))
        if self._species_skill_grants:
            grant_txt = ", ".join(
                f"{n} {d}" for n, d in sorted(self._species_skill_grants.items())
            )
            tk.Label(
                self.content_frame,
                text=f"Species grants (no extra skill cost to listed die): {grant_txt}",
                font=("Segoe UI", 9),
                fg="gray",
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(0, 6))

        all_skills = sorted([s for s in SKILL_ATTRIBUTES if s not in CORE_SKILLS])
        all_skills += list(CORE_SKILLS)

        skills_frame = tk.Frame(self.content_frame)
        skills_frame.pack(fill=tk.BOTH, expand=True)

        left_table = tk.Frame(skills_frame)
        left_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        right_table = tk.Frame(skills_frame)
        right_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.skill_vars = {}

        def make_skill_up(skill_name):
            def up():
                current_val = self.skill_vars[skill_name].get()
                if current_val == "Untrained":
                    self.skill_vars[skill_name].set("d4")
                    self._recalc_skill_pts()
                    if self.skill_pts_remaining < 0:
                        self.skill_vars[skill_name].set("Untrained")
                        self._recalc_skill_pts()
                    return

                current = die_to_num(current_val)
                if current >= 12:
                    return
                next_die = num_to_die(current + 2)
                self.skill_vars[skill_name].set(next_die)
                self._recalc_skill_pts()
                if self.skill_pts_remaining < 0:
                    # Revert if player can't afford the increase.
                    self.skill_vars[skill_name].set(num_to_die(current))
                    self._recalc_skill_pts()

            return up

        def make_skill_down(skill_name):
            def down():
                current_val = self.skill_vars[skill_name].get()
                if current_val == "Untrained":
                    return
                current = die_to_num(current_val)
                grant_die = self._species_skill_grants.get(skill_name)
                if grant_die:
                    floor = die_to_num(grant_die)
                    if skill_name in core_skills:
                        floor = max(4, floor)
                    if current <= floor:
                        return
                if skill_name not in core_skills and current == 4:
                    self.skill_vars[skill_name].set("Untrained")
                    self._recalc_skill_pts()
                    return
                if current <= 4:
                    return
                self.skill_vars[skill_name].set(num_to_die(current - 2))
                self._recalc_skill_pts()

            return down

        def build_table_header(parent):
            tk.Label(parent, text="Skill", width=16, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
            tk.Label(parent, text="Attr", width=8, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
            tk.Label(parent, text="Die", width=4, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")

        def build_skill_row(parent, row_idx, skill_name):
            if skill_name not in self.char.skills:
                self.char.skills[skill_name] = "d4" if skill_name in core_skills else "Untrained"
            tk.Label(parent, text=skill_name, width=16, anchor=tk.W).grid(row=row_idx, column=0, sticky="w", pady=1)
            linked = SKILL_ATTRIBUTES.get(skill_name, "Smarts")
            tk.Label(parent, text=linked, width=8, anchor=tk.W, fg="gray").grid(row=row_idx, column=1, sticky="w", pady=1)
            var = tk.StringVar(value=self.char.skills[skill_name])
            self.skill_vars[skill_name] = var
            tk.Label(parent, textvariable=var, width=4, anchor=tk.W).grid(row=row_idx, column=2, sticky="w", pady=1)
            tk.Button(parent, text="+", command=make_skill_up(skill_name), width=2).grid(row=row_idx, column=3, padx=2)
            tk.Button(parent, text="-", command=make_skill_down(skill_name), width=2).grid(row=row_idx, column=4)

        build_table_header(left_table)
        build_table_header(right_table)
        split_index = (len(all_skills) + 1) // 2
        left_skills = all_skills[:split_index]
        right_skills = all_skills[split_index:]

        for idx, skill in enumerate(left_skills, start=1):
            build_skill_row(left_table, idx, skill)
        for idx, skill in enumerate(right_skills, start=1):
            build_skill_row(right_table, idx, skill)

        self._recalc_skill_pts()
        self.skill_pts_label = tk.Label(
            self.content_frame,
            text=f"Skill points remaining: {self.skill_pts_remaining}",
            font=("Segoe UI", 10, "bold"),
        )
        self.skill_pts_label.pack(pady=10)

        def save():
            for sk, var in self.skill_vars.items():
                value = var.get()
                if sk in core_skills:
                    self.char.skills[sk] = "d4" if value == "Untrained" else value
                else:
                    if value == "Untrained":
                        self.char.skills.pop(sk, None)
                    else:
                        self.char.skills[sk] = value
            pts_spent = total_pts - self.skill_pts_remaining
            self.char.hindrance_points_remaining = max(
                0,
                self.char.hindrance_points_remaining - max(0, pts_spent - 15),
            )

        self._save_step = save

    def step_edges(self):
        if not hasattr(self.char, "human_free_edges_used"):
            self.char.human_free_edges_used = []
        is_human = self.char.species == "Human"
        human_free_left = 1 - len(self.char.human_free_edges_used)

        pts_text = f"Hindrance points remaining: {self.char.hindrance_points_remaining}"
        if is_human and human_free_left > 0:
            pts_text += f"  |  Human bonus: {human_free_left} free Edge(s)"
        tk.Label(
            self.content_frame,
            text=pts_text,
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Each Edge costs 2 hindrance points (Humans get 1 free Edge).",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        list_frame = tk.Frame(self.content_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="Available Edges", font=("Segoe UI", 9, "bold")).pack()
        lb_avail = tk.Listbox(list_frame, height=10, font=("Segoe UI", 10))
        lb_avail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        all_edge_names = sorted(
            EDGES.keys(),
            key=lambda e: (
                _edge_category_from_data(e, EDGES[e]),
                ["Novice", "Seasoned", "Veteran", "Heroic", "Legendary"].index(
                    _edge_rank_from_requirements(EDGES[e].get("requirements", ""))
                ),
                e,
            ),
        )
        for e in all_edge_names:
            if e not in self.char.edges:
                label = _edge_list_label(e, EDGES[e])
                lb_avail.insert(tk.END, label)
                idx = lb_avail.size() - 1
                missing = _edge_missing_attribute_requirements(
                    EDGES[e], self.char.attributes
                )
                missing += _edge_missing_skill_requirements(
                    EDGES[e], self.char.skills
                )
                if missing:
                    lb_avail.itemconfig(idx, fg="gray")

        def add_edge():
            sel = lb_avail.curselection()
            if not sel:
                return
            idx = sel[0]
            edge_label = lb_avail.get(idx)
            edge = _edge_name_from_list_label(edge_label)
            missing = _edge_missing_attribute_requirements(
                EDGES.get(edge, {}), self.char.attributes
            )
            missing += _edge_missing_skill_requirements(
                EDGES.get(edge, {}), self.char.skills
            )
            if missing:
                messagebox.showinfo(
                    "Requirements not met",
                    "Missing requirement(s): " + ", ".join(missing),
                )
                return
            can_use_free = is_human and len(self.char.human_free_edges_used) < 1
            if can_use_free:
                self.char.human_free_edges_used.append(edge)
            elif self.char.hindrance_points_remaining >= 2:
                self.char.hindrance_points_remaining -= 2
            else:
                messagebox.showinfo(
                    "No points",
                    "Need 2 hindrance points to take an Edge (or use your Human free Edge if available).",
                )
                return
            self.char.edges.append(edge)
            lb_avail.delete(idx)
            lb_chosen.insert(tk.END, _edge_list_label(edge, EDGES.get(edge, {})))
            human_left = 1 - len(self.char.human_free_edges_used)
            lbl = f"Hindrance points: {self.char.hindrance_points_remaining}"
            if is_human and human_left > 0:
                lbl += f"  |  Human free: {human_left}"
            self.edge_pts_label.config(text=lbl)

        btn_add = tk.Button(list_frame, text="Add →", command=add_edge)
        btn_add.pack(side=tk.LEFT, padx=5)

        tk.Label(list_frame, text="Chosen", font=("Segoe UI", 9, "bold")).pack()
        lb_chosen = tk.Listbox(list_frame, height=10, font=("Segoe UI", 10))
        lb_chosen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for e in self.char.edges:
            lb_chosen.insert(tk.END, _edge_list_label(e, EDGES.get(e, {})))

        def remove_edge():
            sel = lb_chosen.curselection()
            if not sel:
                return
            idx = sel[0]
            edge_label = lb_chosen.get(idx)
            edge = _edge_name_from_list_label(edge_label)
            self.char.edges.remove(edge)
            lb_chosen.delete(idx)
            lb_avail.insert(tk.END, _edge_list_label(edge, EDGES.get(edge, {})))
            if edge in self.char.human_free_edges_used:
                self.char.human_free_edges_used.remove(edge)
            else:
                self.char.hindrance_points_remaining += 2
            human_left = 1 - len(self.char.human_free_edges_used)
            lbl = f"Hindrance points: {self.char.hindrance_points_remaining}"
            if is_human and human_left > 0:
                lbl += f"  |  Human free: {human_left}"
            self.edge_pts_label.config(text=lbl)

        tk.Button(list_frame, text="← Remove", command=remove_edge).pack(
            side=tk.LEFT, padx=5
        )

        lbl = f"Hindrance points: {self.char.hindrance_points_remaining}"
        if is_human and human_free_left > 0:
            lbl += f"  |  Human free: {human_free_left}"
        self.edge_pts_label = tk.Label(
            self.content_frame,
            text=lbl,
            font=("Segoe UI", 10),
        )
        self.edge_pts_label.pack(pady=10)

        tk.Label(
            self.content_frame,
            text="Click an edge in either list to see requirements and effects.",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(4, 2))

        edge_details_txt = scrolledtext.ScrolledText(
            self.content_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            height=6,
            state=tk.DISABLED,
        )
        edge_details_txt.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        def show_edge_details(evt):
            w = evt.widget
            sel = w.curselection()
            if not sel:
                return
            edge_name = _edge_name_from_list_label(w.get(sel[0]))
            detail = format_edge_details(edge_name, EDGES.get(edge_name, {}))
            edge_details_txt.config(state=tk.NORMAL)
            edge_details_txt.delete("1.0", tk.END)
            edge_details_txt.insert("1.0", detail)
            edge_details_txt.config(state=tk.DISABLED)

        lb_avail.bind("<<ListboxSelect>>", show_edge_details)
        lb_chosen.bind("<<ListboxSelect>>", show_edge_details)

        self._save_step = lambda: None

    def step_weapons(self):
        recalc_credits(self.char)

        tk.Label(
            self.content_frame,
            text=f"Credits: {self.char.credits}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Select weapons to buy (costs deducted from starting credits):",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        weapons_frame = tk.Frame(self.content_frame)
        weapons_frame.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(weapons_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left, text="Available (select & Buy)", font=("Segoe UI", 9)).pack()
        lb_avail = tk.Listbox(left, height=10, font=("Segoe UI", 10))
        lb_avail.pack(fill=tk.BOTH, expand=True)
        for w, d in WEAPONS.items():
            if w not in self.char.weapons:
                lb_avail.insert(tk.END, f"{w} - {d['cost']} cr")

        def show_weapon_details(evt):
            for lb in (lb_avail, lb_chosen):
                sel = lb.curselection()
                if sel:
                    item = lb.get(sel[0]).rsplit(" - ", 1)[0].strip()
                    detail = format_item_details(item, WEAPONS.get(item, ALL_GEAR.get(item, {})))
                    details_txt.config(state=tk.NORMAL)
                    details_txt.delete("1.0", tk.END)
                    details_txt.insert("1.0", detail)
                    details_txt.config(state=tk.DISABLED)
                    return

        def add_weapon():
            sel = lb_avail.curselection()
            if not sel:
                return
            item = lb_avail.get(sel[0]).split(" - ")[0]
            cost = WEAPONS[item]["cost"]
            if self.char.credits >= cost and item not in self.char.weapons:
                self.char.weapons.append(item)
                self.char.credits -= cost
                lb_avail.delete(sel[0])
                lb_chosen.insert(tk.END, f"{item} - {cost} cr")
                self.weapon_credits_label.config(
                    text=f"Credits remaining: {self.char.credits}"
                )

        def remove_weapon():
            sel = lb_chosen.curselection()
            if not sel:
                return
            item = lb_chosen.get(sel[0]).split(" - ")[0]
            cost = WEAPONS[item]["cost"]
            self.char.weapons.remove(item)
            self.char.credits += cost
            lb_chosen.delete(sel[0])
            lb_avail.insert(tk.END, f"{item} - {cost} cr")
            self.weapon_credits_label.config(
                text=f"Credits remaining: {self.char.credits}"
            )

        mid = tk.Frame(weapons_frame)
        mid.pack(side=tk.LEFT, padx=10)
        tk.Button(mid, text="Buy →", command=add_weapon).pack(pady=5)
        tk.Button(mid, text="← Sell", command=remove_weapon).pack(pady=5)

        right = tk.Frame(weapons_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="Your weapons (select to sell)", font=("Segoe UI", 9)).pack()
        lb_chosen = tk.Listbox(right, height=10, font=("Segoe UI", 10))
        lb_chosen.pack(fill=tk.BOTH, expand=True)
        for w in self.char.weapons:
            lb_chosen.insert(tk.END, f"{w} - {WEAPONS[w]['cost']} cr")

        lb_avail.bind("<<ListboxSelect>>", show_weapon_details)
        lb_chosen.bind("<<ListboxSelect>>", show_weapon_details)

        tk.Label(self.content_frame, text="Details (select an item)", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(10, 2))
        details_txt = scrolledtext.ScrolledText(
            self.content_frame, height=6, font=("Segoe UI", 9),
            wrap=tk.WORD, state=tk.DISABLED, bg="#f5f5f5", relief=tk.FLAT, padx=8, pady=5
        )
        details_txt.pack(fill=tk.X, pady=(0, 10))

        self.weapon_credits_label = tk.Label(
            self.content_frame,
            text=f"Credits remaining: {self.char.credits}",
            font=("Segoe UI", 10),
        )
        self.weapon_credits_label.pack(pady=10)

        self._save_step = lambda: None

    def step_armor_gear(self):
        recalc_credits(self.char)

        tk.Label(
            self.content_frame,
            text=f"Credits: {self.char.credits}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            self.content_frame,
            text="Weapons, armor, and gear — buy/sell with credits:",
            font=("Segoe UI", 9),
            fg="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        tk.Label(
            self.content_frame,
            text="Details (select a weapon, armor, or gear item)",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, pady=(0, 2))
        equip_details_txt = scrolledtext.ScrolledText(
            self.content_frame,
            height=6,
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f5f5f5",
            relief=tk.FLAT,
            padx=8,
            pady=5,
        )
        equip_details_txt.pack(fill=tk.X, pady=(0, 10))

        # Weapons section
        tk.Label(
            self.content_frame, text="Weapons", font=("Segoe UI", 10)
        ).pack(anchor=tk.W, pady=(0, 5))

        weapons_frame = tk.Frame(self.content_frame)
        weapons_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        weap_left = tk.Frame(weapons_frame)
        weap_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(weap_left, text="Available (select & Buy)", font=("Segoe UI", 9)).pack()
        lb_weap_avail = tk.Listbox(weap_left, height=5, font=("Segoe UI", 10))
        lb_weap_avail.pack(fill=tk.BOTH, expand=True)
        for w, d in WEAPONS.items():
            if w not in self.char.weapons:
                lb_weap_avail.insert(tk.END, f"{w} - {d['cost']} cr")

        def show_weapon_details(evt):
            for lb in (lb_weap_avail, lb_weap_owned):
                sel = lb.curselection()
                if sel:
                    item = lb.get(sel[0]).rsplit(" - ", 1)[0].strip()
                    detail = format_item_details(item, WEAPONS.get(item, ALL_GEAR.get(item, {})))
                    equip_details_txt.config(state=tk.NORMAL)
                    equip_details_txt.delete("1.0", tk.END)
                    equip_details_txt.insert("1.0", detail)
                    equip_details_txt.config(state=tk.DISABLED)
                    return

        def add_weapon():
            sel = lb_weap_avail.curselection()
            if not sel:
                return
            item = lb_weap_avail.get(sel[0]).split(" - ")[0]
            cost = WEAPONS[item]["cost"]
            if self.char.credits >= cost and item not in self.char.weapons:
                self.char.weapons.append(item)
                self.char.credits -= cost
                lb_weap_avail.delete(sel[0])
                lb_weap_owned.insert(tk.END, f"{item} - {cost} cr")
                self.gear_credits_label.config(
                    text=f"Credits remaining: {self.char.credits}"
                )

        def remove_weapon():
            sel = lb_weap_owned.curselection()
            if not sel:
                return
            item = lb_weap_owned.get(sel[0]).split(" - ")[0]
            cost = WEAPONS[item]["cost"]
            self.char.weapons.remove(item)
            self.char.credits += cost
            lb_weap_owned.delete(sel[0])
            lb_weap_avail.insert(tk.END, f"{item} - {cost} cr")
            self.gear_credits_label.config(
                text=f"Credits remaining: {self.char.credits}"
            )

        weap_mid = tk.Frame(weapons_frame)
        weap_mid.pack(side=tk.LEFT, padx=10)
        tk.Button(weap_mid, text="Buy →", command=add_weapon).pack(pady=5)
        tk.Button(weap_mid, text="← Sell", command=remove_weapon).pack(pady=5)

        weap_right = tk.Frame(weapons_frame)
        weap_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(weap_right, text="Your weapons (select to sell)", font=("Segoe UI", 9)).pack()
        lb_weap_owned = tk.Listbox(weap_right, height=5, font=("Segoe UI", 10))
        lb_weap_owned.pack(fill=tk.BOTH, expand=True)
        for w in self.char.weapons:
            lb_weap_owned.insert(tk.END, f"{w} - {WEAPONS[w]['cost']} cr")

        lb_weap_avail.bind("<<ListboxSelect>>", show_weapon_details)
        lb_weap_owned.bind("<<ListboxSelect>>", show_weapon_details)

        # Armor section
        armor_frame = tk.Frame(self.content_frame)
        armor_frame.pack(fill=tk.X, pady=(0, 10))

        armor_left = tk.Frame(armor_frame)
        armor_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(armor_left, text="Available armor", font=("Segoe UI", 9)).pack()
        lb_armor_avail = tk.Listbox(armor_left, height=4, font=("Segoe UI", 10))
        lb_armor_avail.pack(fill=tk.BOTH, expand=True)
        for a, d in ARMOR.items():
            if a != self.char.armor:
                lb_armor_avail.insert(tk.END, f"{a} - {d['cost']} cr")

        def show_armor_details(evt):
            for lb in (lb_armor_avail, lb_armor_owned):
                sel = lb.curselection()
                if sel:
                    item = lb.get(sel[0]).rsplit(" - ", 1)[0].strip()
                    detail = format_item_details(item, ARMOR.get(item, ALL_GEAR.get(item, {})))
                    equip_details_txt.config(state=tk.NORMAL)
                    equip_details_txt.delete("1.0", tk.END)
                    equip_details_txt.insert("1.0", detail)
                    equip_details_txt.config(state=tk.DISABLED)
                    return

        def buy_armor():
            sel = lb_armor_avail.curselection()
            if not sel:
                return
            item = lb_armor_avail.get(sel[0]).split(" - ")[0]
            cost = ARMOR[item]["cost"]
            old_cost = ARMOR.get(self.char.armor, {}).get("cost", 0)
            net_cost = cost - old_cost
            if self.char.credits >= net_cost:
                if self.char.armor and self.char.armor != "No Armor":
                    lb_armor_owned.delete(0)
                    lb_armor_avail.insert(tk.END, f"{self.char.armor} - {old_cost} cr")
                self.char.armor = item
                self.char.credits -= net_cost
                lb_armor_avail.delete(sel[0])
                lb_armor_owned.insert(tk.END, f"{item} - {cost} cr")
                self.gear_credits_label.config(
                    text=f"Credits remaining: {self.char.credits}"
                )

        def sell_armor():
            if not self.char.armor or self.char.armor == "No Armor":
                return
            item = self.char.armor
            cost = ARMOR[item]["cost"]
            self.char.armor = "No Armor"
            self.char.credits += cost
            lb_armor_owned.delete(0)
            lb_armor_avail.insert(tk.END, f"{item} - {cost} cr")
            self.gear_credits_label.config(
                text=f"Credits remaining: {self.char.credits}"
            )

        armor_mid = tk.Frame(armor_frame)
        armor_mid.pack(side=tk.LEFT, padx=10)
        tk.Label(armor_mid, text="", font=("Segoe UI", 9)).pack()
        tk.Button(armor_mid, text="Equip →", command=buy_armor).pack(pady=2)
        tk.Button(armor_mid, text="← Remove", command=sell_armor).pack(pady=2)

        armor_right = tk.Frame(armor_frame)
        armor_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(armor_right, text="Your armor (worn)", font=("Segoe UI", 9)).pack()
        lb_armor_owned = tk.Listbox(armor_right, height=4, font=("Segoe UI", 10))
        lb_armor_owned.pack(fill=tk.BOTH, expand=True)
        if self.char.armor and self.char.armor != "No Armor":
            lb_armor_owned.insert(tk.END, f"{self.char.armor} - {ARMOR[self.char.armor]['cost']} cr")

        lb_armor_avail.bind("<<ListboxSelect>>", show_armor_details)
        lb_armor_owned.bind("<<ListboxSelect>>", show_armor_details)

        # Gear section
        tk.Label(
            self.content_frame, text="Gear", font=("Segoe UI", 10)
        ).pack(anchor=tk.W, pady=(10, 5))

        gear_frame = tk.Frame(self.content_frame)
        gear_frame.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(gear_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left, text="Available (select & Buy)", font=("Segoe UI", 9)).pack()
        lb_gear = tk.Listbox(left, height=6, font=("Segoe UI", 10))
        lb_gear.pack(fill=tk.BOTH, expand=True)
        for g, d in GEAR.items():
            if g not in self.char.gear:
                lb_gear.insert(tk.END, f"{g} - {d['cost']} cr")

        mid = tk.Frame(gear_frame)
        mid.pack(side=tk.LEFT, padx=10)

        right = tk.Frame(gear_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="Your gear (select to sell)", font=("Segoe UI", 9)).pack()
        lb_owned = tk.Listbox(right, height=6, font=("Segoe UI", 10))
        lb_owned.pack(fill=tk.BOTH, expand=True)
        for g in self.char.gear:
            lb_owned.insert(tk.END, f"{g} - {GEAR[g]['cost']} cr")

        def show_gear_details(evt):
            for lb in (lb_gear, lb_owned):
                sel = lb.curselection()
                if sel:
                    item = lb.get(sel[0]).rsplit(" - ", 1)[0].strip()
                    detail = format_item_details(item, GEAR.get(item, ALL_GEAR.get(item, {})))
                    equip_details_txt.config(state=tk.NORMAL)
                    equip_details_txt.delete("1.0", tk.END)
                    equip_details_txt.insert("1.0", detail)
                    equip_details_txt.config(state=tk.DISABLED)
                    return

        lb_gear.bind("<<ListboxSelect>>", show_gear_details)
        lb_owned.bind("<<ListboxSelect>>", show_gear_details)

        def buy_gear():
            sel = lb_gear.curselection()
            if not sel:
                return
            item = lb_gear.get(sel[0]).split(" - ")[0]
            cost = GEAR[item]["cost"]
            if self.char.credits >= cost and item not in self.char.gear:
                self.char.gear.append(item)
                self.char.credits -= cost
                lb_gear.delete(sel[0])
                lb_owned.insert(tk.END, f"{item} - {cost} cr")
                self.gear_credits_label.config(
                    text=f"Credits remaining: {self.char.credits}"
                )

        def sell_gear():
            sel = lb_owned.curselection()
            if not sel:
                return
            item = lb_owned.get(sel[0]).split(" - ")[0]
            cost = GEAR[item]["cost"]
            self.char.gear.remove(item)
            self.char.credits += cost
            lb_owned.delete(sel[0])
            lb_gear.insert(tk.END, f"{item} - {cost} cr")
            self.gear_credits_label.config(
                text=f"Credits remaining: {self.char.credits}"
            )

        tk.Button(mid, text="Buy →", command=buy_gear).pack(pady=5)
        tk.Button(mid, text="← Sell", command=sell_gear).pack(pady=5)

        self.gear_credits_label = tk.Label(
            self.content_frame,
            text=f"Credits remaining: {self.char.credits}",
            font=("Segoe UI", 10),
        )
        self.gear_credits_label.pack(pady=5)

        self._save_step = lambda: None

    def step_summary(self):
        self._save_step = lambda: None

        summary = scrolledtext.ScrolledText(
            self.content_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            height=20,
        )
        summary.pack(fill=tk.BOTH, expand=True)

        summary.insert(tk.END, character_sheet_text(self.char.to_dict()))
        summary.config(state=tk.DISABLED)

        btn_row = tk.Frame(self.content_frame)
        btn_row.pack(pady=10)

        def do_save():
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=_character_filename(self.char),
            )
            if path:
                with open(path, "w") as f:
                    json.dump(self.char.to_dict(), f, indent=2)
                messagebox.showinfo("Saved", f"Character saved to {path}")
                self.root.quit()

        def export_html_sheet():
            base = (self.char.name or "character").strip() or "character"
            for c in '\\/:*?"<>|':
                base = base.replace(c, "_")
            path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
                initialfile=f"{base}.html",
            )
            if path:
                html_doc = character_sheet_html(self.char.to_dict())
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html_doc)
                messagebox.showinfo("Exported", f"Printable sheet saved to {path}")

        def export_text_sheet():
            base = (self.char.name or "character").strip() or "character"
            for c in '\\/:*?"<>|':
                base = base.replace(c, "_")
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"{base}-sheet.txt",
            )
            if path:
                text_doc = character_sheet_text(self.char.to_dict())
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text_doc)
                messagebox.showinfo("Exported", f"Text sheet saved to {path}")

        tk.Button(
            btn_row,
            text="Save to JSON File",
            font=("Segoe UI", 10),
            command=do_save,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            btn_row,
            text="Export printable HTML…",
            font=("Segoe UI", 10),
            command=export_html_sheet,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            btn_row,
            text="Export text sheet…",
            font=("Segoe UI", 10),
            command=export_text_sheet,
        ).pack(side=tk.LEFT, padx=6)

    def run(self):
        def on_next():
            if hasattr(self, "_save_step") and self._save_step:
                try:
                    self._save_step()
                except Exception:
                    pass
            if self.current_step < len(self.steps) - 1:
                self._show_step(self.current_step + 1)
            else:
                path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile=_character_filename(self.char),
                )
                if path:
                    with open(path, "w") as f:
                        json.dump(self.char.to_dict(), f, indent=2)
                    messagebox.showinfo("Saved", f"Character saved to {path}")
                self.root.quit()

        self.btn_next.config(command=on_next)
        self.root.mainloop()


def main():
    app = CharacterBuilderApp()
    app.run()
    print("May the Force be with you!")


if __name__ == "__main__":
    main()
