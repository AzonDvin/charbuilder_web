# Savage Worlds Star Wars Character Builder

You can use a **desktop wizard** (Tkinter) or a **local web app** (FastAPI) to create **Savage Worlds** Star Wars characters. Game data lives in JSON (species, hindrances, edges, gear, **careers**, and so on); exports are written as `.json` (and optional HTML/text sheets).

The web UI is a **single top-down page** (no step-by-step wizard). It is intended for **local use** (default bind `127.0.0.1`) with **no authentication**.

## Current Project Process

The character builder walks through this process in order:

1. **Concept, species & career** - Set character name, species, and **career** (from `data/careers.json`). Careers are free at creation; **benefits** (not the internal `desc`) appear on exported sheets.
2. **Hindrances** - Select up to 4 hindrance points (Major = 2, Minor = 1).
3. **Attributes** - Spend base attribute points plus any converted hindrance points.
4. **Skills** - Spend base skill points plus any converted hindrance points.
5. **Edges** - Purchase edges with hindrance points (2 points each). Human gets one free edge.
6. **Weapons, Armor & Gear** - Buy equipment using starting credits.
7. **Summary** - Review final sheet and save to JSON.

## Features Implemented

- Desktop: guided multi-step UI flow with Previous/Next navigation.
- Web: one-page builder with live preview and saves into the `output/` folder on the host machine.
- Species-aware setup (including Human free-edge handling).
- **Careers** (web and desktop concept step): optional job packages; **benefits only** are shown in the UI and on printed/text/HTML sheets (career `desc` in JSON is optional author notes and is not published anywhere in the app).
- Hindrance point tracking across attributes, skills, and edges.
- Edge requirement checks for rank, attributes, and skills.
- Equipment shop with buy/sell and live credit recalculation.
- Derived stat calculation (`Toughness` and `Parry`).
- Final character export to `.json`.
- Optional **print-friendly** exports: HTML layout or plain text (from the Summary step, or from a saved JSON file via CLI).

## Run the Project

### Requirements

- Python 3.10+ (Tkinter included with standard Python installs for the desktop app)
- Web UI: install dependencies with `pip install -r requirements.txt`

### Start (desktop wizard)

From the project root:

```bash
python main.py
```

### Start (local web UI)

```bash
pip install -r requirements.txt
python main.py --web
```

Then open **http://127.0.0.1:8000** in your browser. Use **Save to `output/`** to write JSON / HTML / text exports next to the project (the `output/` directory is created automatically).

## Project Structure

- `main.py` - Entry point (`python main.py` = desktop; `python main.py --web` = FastAPI).
- `web_api.py` - FastAPI app and `/api/meta`, `/api/preview`, `/api/save` routes.
- `rules.py` - Shared credit and hindrance/edge helpers (used by `gui.py` and `web_api.py`).
- `templates/builder.html`, `static/builder.js` - Web UI.
- `gui.py` - Tkinter wizard UI and step logic.
- `character.py` - Character model and derived stat logic.
- `character_sheet.py` - Text/HTML character sheet from exported JSON (used by CLI and Summary exports).
- `data.py` - JSON data loader and data grouping.
- `data/` - Source game content:
  - `attributes.json`
  - `careers.json` — career `desc` (optional, unused by the app) and `benefits` (shown in UI and exports)
  - `edges.json`
  - `gear.json`
  - `hindrances.json`
  - `species.json`
- `docs/race_building_rules.md` - Reference notes for custom race/species design.

## Data-Driven Content

Most rules content is loaded from JSON files in `data/`. To expand options:

- Add or edit edges in `data/edges.json`
- Add or edit hindrances in `data/hindrances.json`
- Add or edit species in `data/species.json`
- Add or edit careers in `data/careers.json` (each entry: optional `desc` for your own notes; `benefits` array of `{ "title", "type", "effect" }` objects is what players see)
- Add or edit equipment in `data/gear.json`
- Update skills/attributes in `data/attributes.json`

## Save Output

When the build is complete, the app saves a character JSON that includes:

- Character identity, species data, and **`career`** (career name; text/HTML sheets list **benefits** from `careers.json`, not `desc`)
- Attributes and skills
- Hindrances and edges
- Equipment and credits
- Derived values (`toughness`, `parry`)

## Display and print from JSON

After you have a character `.json` file, you can turn it into something easy to read or print in several ways:

1. **Summary step in the app** — On the last step, use **Export printable HTML…** or **Export text sheet…** (same layout as the on-screen summary, plus a styled HTML page for printing).

2. **Command-line renderer** — From the project directory (so `data/` can resolve armor names for the armor bonus line):

   ```bash
   python character_sheet.py path/to/character.json --html sheet.html --open
   ```

   Other flags:

   - `--text sheet.txt` — plain text sheet
   - `--stdout` — print plain text to the terminal
   - With no `--html` / `--text` / `--stdout`, prints plain text and a short tip on stderr

3. **Browser print to PDF** — Open the generated HTML, use the browser’s **Print** dialog, and choose **Save as PDF** if you want a PDF without extra Python libraries.

4. **Bring your own template** — The JSON is a simple structure (`name`, `species`, `career`, `attributes`, `skills`, `edges`, etc.). You can import it into a word processor, Obsidian, or another tool and format it however you like.

The logic for the text/HTML sheet lives in `character_sheet.py` (`character_sheet_text`, `character_sheet_html`).

## Notes

- Web **preview** and **save** require both **species** and **career** to match entries in `data/species.json` and `data/careers.json`. Older exports without `career` need a career selected before validation passes.
- Existing docs include race balancing guidance in `docs/race_building_rules.md`.
- `requirements.txt` lists **FastAPI**, **uvicorn**, and **pydantic** for the web UI; the desktop wizard uses the standard library only (plus the same project modules).
