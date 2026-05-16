# Savage Worlds Star Wars Character Builder

This is a character builder for playing **Star Wars using the Savage Worlds Adventure Edition (SWADE)** ruleset. If your group is running a Star Wars tabletop campaign with SWADE, this tool walks you through making a character and spits out a finished sheet you can bring to the table.

It runs two ways: as a **local web app** you open in your browser, or as a **desktop wizard** on Windows/Mac/Linux. Either way it's self-contained — no account, no internet connection, no server to host.

---

## What it does

You pick a species (Wookiee, Twi'lek, Droid, etc.), a career background (Smuggler, Bounty Hunter, Medic, etc.), and then spend your points on attributes, skills, edges, and gear. The app enforces the rules as you go — edge prerequisites, hindrance point limits, credit costs — so you don't have to keep the rulebook open.

When you're done it saves a character file and can export a **print-ready HTML sheet** styled like the official Savage Worlds record sheet.

---

## Getting started

You need **Python 3.10 or newer**.

**Run the web UI** (recommended — works in any browser):

```bash
pip install -r requirements.txt
python main.py --web
```

Then open **http://127.0.0.1:8000** in your browser.

**Run the desktop app** (no extra dependencies):

```bash
python main.py
```

Saved characters and exported sheets land in the `output/` folder, which is created automatically the first time you save.

---

## Character creation steps

The builder walks you through these in order:

1. **Concept, Species & Career** — Name your character, choose a species and a career background. Careers are free — they give you narrative flavor and a few small mechanical benefits, not power picks.
2. **Hindrances** — Take up to 4 points of hindrances (Major = 2 pts, Minor = 1 pt) to earn extra points for later steps.
3. **Attributes** — Spend your attribute points to raise Agility, Smarts, Spirit, Strength, and Vigor. Die steps go d4 → d6 → d8 → d10 → d12.
4. **Skills** — Spend skill points to buy and raise skills. Skills linked to your attributes are cheaper to raise.
5. **Edges** — Spend hindrance points on edges (special abilities). Each edge costs 2 hindrance points. Humans get one free edge at creation.
6. **Gear** — Buy weapons, armor, and equipment from the shop using your starting credits.
7. **Summary** — Review everything and export your finished sheet.

Starting credits depend on your wealth hindrances: standard 500 cr, Poverty (Minor) 250 cr, Poverty (Major) 125 cr, Rich 1,500 cr, Filthy Rich 2,500 cr.

---

## Exporting your sheet

At the Summary step you can export:

- **Printable HTML** — A styled sheet matching the official Savage Worlds record sheet layout. Open it in a browser and use Print → Save as PDF.
- **Plain text** — A simple text version for pasting into notes or a VTT.

You can also render a sheet from any saved `.json` file on the command line:

```bash
python character_sheet.py output/my_character.json --html sheet.html --open
python character_sheet.py output/my_character.json --text sheet.txt
python character_sheet.py output/my_character.json --stdout
```

---

## Adding your own content

Everything is data-driven. **You don't need to touch any Python code** to add a new species, edge, weapon, or career — just edit the JSON files in `data/` and restart the app.

| File | What's in it |
|------|-------------|
| `data/species.json` | 17 playable species with abilities and lore notes |
| `data/careers.json` | 8 career backgrounds with narrative benefits |
| `data/edges.json` | 33 edges with prerequisites and effects |
| `data/hindrances.json` | Hindrances with Minor/Major classification |
| `data/attributes.json` | The full skill list and which attribute each skill links to |
| `data/gear.json` | Weapons (damage, range, notes), armor, and gear items |

After editing any data file, regenerate the reference manual so it stays current:

```bash
python scripts/generate_character_manual.py
```

This writes `docs/character_manual.html` — a browsable reference covering all species, careers, edges, hindrances, and gear in one page.

Guidance on designing balanced species from scratch (point-buy system, worked examples) is in `docs/race_building_rules.md`.

---

## Rules accuracy

The skill list, edges, and species abilities have all been audited against **SWADE core rules** and trimmed to fit a Star Wars setting:

- Skills that don't belong in Star Wars (Boating, Riding) have been removed.
- `Streetwise` (dropped in SWADE AE) is replaced by Persuasion, Notice, and Common Knowledge where appropriate.
- `Hacking` / `Use Computer` are replaced by `Slicing` — the Star Wars equivalent and the SWADE AE approach.
- All 33 edges have been checked for correct prerequisites and effect wording against SWADE AE.
- `Force-Sensitive` is a Novice edge, available to any species — Force ability is not locked to a species trait.

---

## Project layout

```
charbuilder_web/
├── main.py               # Start here — runs desktop or web UI
├── web_api.py            # FastAPI routes and API logic
├── character.py          # Character model; calculates Toughness and Parry
├── character_sheet.py    # Generates the text and HTML exports
├── rules.py              # Credit and hindrance/edge rule helpers
├── data.py               # Loads and groups JSON data files
├── gui.py                # Desktop wizard (Tkinter)
├── templates/builder.html
├── static/builder.js
├── data/                 # All game content — edit these to expand the game
├── docs/                 # Reference manual and design guides
├── scripts/              # generate_character_manual.py
└── output/               # Saved characters (created automatically)
```

---

## Dependencies

The **desktop app** uses only the Python standard library (plus Tkinter, which ships with most Python installs).

The **web UI** requires three packages:

```
fastapi
uvicorn
pydantic
```

Install them with `pip install -r requirements.txt`.
