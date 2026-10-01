# Design notes — forge_app

This is Exeliq's FORGE AI Streamlit app with our integration work on top. The original is at
`Forge_AI/Streamlit_App/` and is never modified.

## Skills used

Two agent skills informed the design work. Both are installed in this repository at
`.agents/skills/` and pinned in `skills-lock.json`, so anyone can read exactly what guidance
was applied.

| Skill | Source | Used for |
|---|---|---|
| `frontend-design` | `anthropics/skills` | Visual direction, typography, spotting generated-looking defaults |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` | Design-system query, accessibility and UX checklists |

### What we took from `ui-ux-pro-max`, and what we rejected

Queried as `"recruitment staffing applicant tracking dashboard" --design-system`. Treating the
output as recommendation rather than instruction, which is what the skill itself asks for:

**Taken**

- **Flat design** — its style match for a staffing dashboard: "no gradients/shadows, clean
  lines, typography-focused". The app was gradienting its brand badge and rounding everything to
  14–16px regardless of hierarchy. The gradient is gone.
- **Fira Sans with Fira Code** — its typography pairing for dashboards and admin panels. The app
  previously specified no typeface at all, so it rendered in whatever Streamlit defaulted to.
  Figures that get compared now sit in Fira Code with tabular numerals so columns line up.
- **One transition speed in the 150–200ms band**, and `cursor: pointer` on everything clickable.
- **The accessibility checklist**, which is where the real findings came from (below).
- **No emoji as icons.** Our Email Agent page had used them for stage marks; they render
  differently on every platform and read badly aloud. Replaced with coloured rules.

**Rejected, with reasons**

- **The palette it recommended** (`#0369A1` professional blue with a green accent). Exeliq's
  brand is indigo `#5B4CF2`, used in their logo, hero and every accent in their own CSS. A brief
  that pins down a visual direction wins over a generic recommendation, so the indigo stays.
- **The "Funnel (3-Step Conversion)" pattern** it returned. That is a marketing landing-page
  pattern — hero, problem, solution, CTA progression. FORGE AI is a signed-in multi-page tool,
  not a conversion funnel. The query matched "dashboard" to the wrong product shape.

## Accessibility findings

Contrast was measured, not estimated. WCAG AA needs 4.5:1 for body text.

| Colour | Was | Now | Note |
|---|---|---|---|
| `#8A8FA3` → `#6E748C` | 3.21:1 | 4.63:1 | **The most-used colour in the app**, 20+ uses, failed for body text |
| `#B4B2A9` → `#6E748C` | 2.13:1 | 4.63:1 | Used at 11px — the smallest text in the lowest-contrast colour |
| `#22C55E` → `#178841` | 2.28:1 | 4.53:1 | Success green, failed badly |
| `#1E8E4C` → `#1C8647` | 4.18:1 | 4.61:1 | Just under |
| `#B8790A` → `#A06909` | 3.63:1 | 4.65:1 | Large text only |
| `#A2A7B8` → `#6E7690` | 2.40:1 | 4.51:1 | Ours, a nav group label |

Hue and saturation were preserved in each case; only lightness moved. Background tints
(`#ECEEF6`, `#EEF0FF`, `#E4F7EA`, `#FFF4E0`) are unchanged — they are surfaces, not text, so a
contrast-against-white figure says nothing about them.

## Structural changes

**Theme.** There was no `.streamlit/config.toml`, so Streamlit's default coral `#FF4B4B` was
the primary colour while the brand is indigo. Every primary button, tab underline and radio dot
rendered in a colour belonging to no part of the design. One accent now, theirs.

**Navigation** (`forge/navigation.py`). Twenty flat rows named after system internals — "JD
Intelligence Agent", "Human Authenticity Engine" — became task-named rows grouped into a
journey, differing by account type because a recruitment desk and a job seeker are doing
different work. Page keys are unchanged, so no page code moved. The FORGE agent names are kept
as per-page subtitles, which is where a product name belongs.

**Auth page.** The opening gradient block said "Welcome to FORGE AI" above the tagline already
printed in the sidebar, occupying the most valuable space on the page while helping nobody decide
anything. Replaced with the one decision that matters at signup: job seeker or recruitment desk.

## Dashboard redesign (approved mockup)

The client supplied a finished dashboard mockup, and it supersedes two of the choices above. A
concrete approved design is a stronger brief than the skill's generic recommendation, so where
they disagree the mockup wins and the skill supplies the checklist.

**Changed from the flat pass**

- **Dark navy sidebar** with the selected page as a filled indigo row. The white sidebar against a
  near-white canvas gave navigation and work no boundary.
- **Soft shadows and tinted surfaces are back**, but on a system: one card radius (18px), one
  shadow, and one tint per stat family (indigo, green, violet, amber, blue).
- **Plus Jakarta Sans replaces Fira Sans / Fira Code.** It is the mockup's typeface and has
  tabular figures, so numbers still align without a monospace face.

**Still from `ui-ux-pro-max`** (re-queried as `"career platform SaaS dashboard job seeker"`; it
returned the same Flat / blue / Funnel answer as before, rejected for the same reasons)

- SVG icons, never emoji, for anything acting as an icon: Lucide inline SVG on the dashboard,
  Streamlit's bundled Material Symbols in the sidebar. The wave in the greeting is content.
- Every text colour measured at 4.5:1 or better on the surface it sits on, including the tints.
- Visible focus rings, 44px sidebar targets, `prefers-reduced-motion` honoured.
- Checked at 1760, 1440 and 400px wide.

**Where the code lives.** Markup helpers are in `forge/ui.py` as pure functions (tested in
`tests/test_forge_ui.py`); sidebar icons are `navigation.ICONS`; styles are the `fx-*` block at
the end of the global stylesheet in `app.py`. Cards are Streamlit containers whose key starts
with `fxcard`, which is how CSS reaches a container that holds real widgets.

**Not carried over from the mockup**

- *Upgrade to Pro.* There is no paid tier, and a button that leads nowhere is worse than none.
- *Week-on-week deltas on the readiness score and conversion rate.* Nothing records history, so
  those would be invented numbers. The figures shown come from the same state as before.
- *"This month" filter on the funnel.* Applications carry no dates to filter by.

## Our footprint in `app.py`

Marked with `Exeliq integration` comments throughout. The Email Agent page itself lives in
`exeliq_email_agent.py` and the navigation in `forge/navigation.py`, so the client can adopt the
work by copying two files and reading a small diff rather than merging a rewrite.
