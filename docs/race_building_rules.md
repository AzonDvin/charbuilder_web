# Savage Worlds: Species Design Guide

*Based on **Savage Worlds Adventure Edition (SWADE)**, with Star Wars setting adaptations.*

---

## Overview

Species in this project are defined in `data/species.json` and are entirely data-driven — no code
changes needed to add a new species. Each entry has an `abilities` string (shown in the UI and on
exports) and an optional `notes` string (lore/flavor, shown in the reference manual).

Every species starts with a **free +2 racial ability** — equivalent to a Human's free Novice Edge.
Additional positive traits must be offset by negative traits of equal point value.

**Example:** A species with a +2 ability and a +1 ability must also carry a –3 in negatives,
or a –2 and a –1.

---

## The Three-Way Test

Before finalising any species, ask:

1. **Canon** — Does this match how the species works in Star Wars?
2. **SWADE** — Does it map cleanly to a SWADE mechanic?
3. **Balance** — Is it roughly equal in power to similar species at the same cost?

---

## Point Cost Chart

### Positive Abilities

| Cost | Ability |
|------|---------|
| **+1** | Free skill at d6 (one skill common to the species) |
| **+1** | Low-light vision or Infravision |
| **+1** | Keen Sense (+2 Notice with one specific sense) |
| **+1** | Natural weapons (e.g. claws Str+d6) |
| **+1** | Immunity to poison *or* disease |
| **+1** | Semi-aquatic (hold breath 15 min; full swim pace) |
| **+1** | Burrowing, Wall Walker, or similar movement mode |
| **+1** | +4 resist one environmental effect (heat, cold, vacuum…) |
| **+1** | +2 resist all environmental effects |
| **+1** | +1 Reach |
| **+2** | Free Novice Edge (ignore requirements except prerequisites) |
| **+2** | Attribute starts at d6 instead of d4 |
| **+2** | +2 Armor (negated by AP weapons) |
| **+2** | +1 Toughness |
| **+2** | +1 Size (usually paired with a drawback) |
| **+2** | +1 Parry |
| **+2** | +2 Charisma |
| **+2** | Aquatic (cannot drown; full Swim pace; free Swimming d6) |
| **+2** | Pace 10 |
| **+2** | Flight (base Pace; may run) |
| **+2** | Construct (see SWADE core — droids only) |
| **+3** | Hardy (second Shaken result does not cause a Wound) |
| **+3** | Free Seasoned Edge (ignore requirements except prerequisites) |
| **+3** | Attribute starts at d8 and may advance to d12+2 |

### Negative Abilities

| Cost | Ability |
|------|---------|
| **–1** | Minor Hindrance baked into the species |
| **–1** | Pace 5 |
| **–1** | –2 Charisma |
| **–1** | Racial Enemy (–4 Charisma vs. one specific group) |
| **–1** | –4 resist one environmental effect |
| **–2** | Major Hindrance baked into the species |
| **–2** | Pace 3 (d4 running die) |
| **–2** | –1 Toughness or –1 Parry |
| **–2** | Cannot speak Basic (must use translator droid or partner) |
| **–2** | Dehydration (must immerse in water 1 hr/24 hrs or become Fatigued, then Incapacitated) |
| **–2** | One attribute costs 2 points per die step at character creation |
| **–3** | One attribute costs 2 points per step at creation *and* 2 Advances to raise in play |
| **–3** | One attribute cannot ever advance beyond d6 |

---

## Quick Reference: Point Values

| Value | Typical Use |
|-------|-------------|
| +3 | Hardy, Seasoned Edge, d8-start attribute |
| +2 | d6-start attribute, Novice Edge, Toughness, Aquatic, Flight |
| +1 | Low-light vision, natural weapons, immunities, skill d6 |
| –1 | Minor Hindrance, Pace 5, Charisma penalty |
| –2 | Major Hindrance, Pace 3, Cannot speak Basic |
| –3 | Hard attribute cap or double advancement cost |

---

## Design Rules and Notes

- **Human baseline** is one free Novice Edge (≈ +2). Humans are the generalist benchmark.
- **No species should feel mandatory** for any build. A Wookiee shouldn't be the only viable tank.
- **No species should feel like a trap.** An experienced player should still find it playable.
- **Unlisted abilities:** Assign a cost based on the closest example in the table above.
- **Flavor matters:** Prefer short, evocative names over long mechanical lists in the abilities string.
- **Force sensitivity is an Edge**, not a species trait. Any species can be Force-Sensitive.

---

## Star Wars Species Examples

These examples use actual species in `data/species.json`.

### Human
*The generalist. Sets the baseline.*

| Trait | Cost |
|-------|------|
| Free Novice Edge (ignore requirements except prerequisites) | +2 (free base) |
| **Total** | **+2** ✓ |

**JSON:** `"One extra Edge at creation (ignore requirements except prerequisites)"`

---

### Wookiee
*Big, strong, can't talk to strangers. Classic brute with a social drawback.*

| Trait | Cost |
|-------|------|
| Free base | +2 |
| Strength starts at d6 | +2 |
| +1 Size | +2 |
| Cannot speak Basic (Minor) | –2 |
| –2 Charisma with strangers | –1 |
| **Total** | **+3** (slightly over cap — GM may adjust) |

**JSON:** `"d6 Strength, +1 Size; Cannot speak Basic (Minor), -2 Charisma with strangers"`

**Design note:** Wookiees are intentionally on the generous side. Their social hindrances
(can't speak Basic, charisma penalty) create real play consequences that justify the power.

---

### Zabrak
*Tough species from Iridonia. Balanced fighter profile.*

| Trait | Cost |
|-------|------|
| Free base | +2 |
| +2 to resist Fear | +1 |
| +1 Toughness (Two hearts) | +2 |
| Stubborn (Minor) | –1 |
| **Total** | **+4** (at the generous end of a 4-cap setting) |

**JSON:** `"+2 to resist Fear, Two hearts (+1 Toughness); Stubborn (Minor)"`

---

### Trandoshan
*Reptilian hunters. Strong combat package offset by social penalties.*

| Trait | Cost |
|-------|------|
| Free base | +2 |
| Climbing d6 | +1 |
| Regeneration (1 wound/day) | +2 |
| Claws (Str+d6) | +1 |
| Cold-blooded (–4 resist cold) | –1 |
| –2 Charisma | –1 |
| **Total** | **+4** |

**JSON:** `"Climbing d6, Regeneration (1 wound/day), Claws (Str+d6); Cold-blooded (-4 resist cold), -2 Charisma"`

---

### Mon Calamari
*Aquatic engineers. Strong utility package with an environmental dependency.*

| Trait | Cost |
|-------|------|
| Free base | +2 |
| Aquatic (full Swim pace, free Swimming d6) | +2 |
| Low-light vision | +1 |
| Repair d6 (shipwright instincts) | +1 |
| Must immerse in water 1 hr/24 hrs or Fatigued | –2 |
| **Total** | **+4** |

**JSON:** `"Aquatic (cannot drown, Swimming d6, full swim Pace), Low-light vision, Repair d6 (shipwright instincts); Must immerse in water 1 hr per 24 hrs or become Fatigued"`

---

## Adding a New Species to the Project

Edit `data/species.json`. Each entry follows this format:

```json
"Species Name": {
  "abilities": "Trait 1, Trait 2; Drawback (Minor)",
  "notes": "Canon lore. Homeworld. Notable characters. Cultural notes."
}
```

**Abilities string conventions:**
- Positive traits come first, separated by commas
- A semicolon separates positives from negatives
- Baked-in hindrances are listed with their severity in parentheses: `Stubborn (Minor)`
- Attribute grants use the format `d6 Strength` (the builder parses this)
- Skill grants use the format `Climbing d6` (the builder parses this)

**Example — Gamorrean (new species):**

```json
"Gamorrean": {
  "abilities": "d6 Strength, +1 Toughness, Natural weapons (tusks Str+d4); Low Smarts (Smarts cannot exceed d6), -2 Charisma",
  "notes": "From Gamorr; green-skinned boar warriors; Jabba's palace guards; loyalty to clan over everything."
}
```

After saving, restart the web server (`python main.py --web`) and regenerate the manual
(`python scripts/generate_character_manual.py`) to see the new species appear everywhere.

---

## Checklist Before Adding a Species

- [ ] Point total is within the GM's cap (usually 2–4)
- [ ] No single positive trait is obviously stronger than similar options at the same cost
- [ ] The species abilities string parses correctly (test in the builder UI)
- [ ] Canon traits are represented (even if abstracted)
- [ ] Notes field has lore context and a notable character reference
- [ ] The three-way test passes: Canon ✓ · SWADE ✓ · Balance ✓
