---
version: 1
slug: "frontend-index-html"
primary_target: "frontend/index.html"
related_targets: ["frontend/login.html"]
---

# Staff dashboard

Scope: every staff panel in `frontend/index.html` plus `frontend/login.html`, including modals and toasts. Visitor mode: Operate.

Audience and job: teachers marking morning attendance on their own phones in a daylit classroom, plus directors and accountants at office desktops handling children, money and staff. Task data comes first; demo data only, with no invented customers.

Constraints: Uzbek Latin and Cyrillic names must both render well; longer Russian strings are coming. Standard web controls only. Phone layout and attendance behaviour from the previous adapt pass are kept.

## Direction contract

THESIS: The staff dashboard as the school class register (sinf jurnali) every teacher already keeps: cloth cover, clean pages, ink and pencil marks. It refuses the dark glass SaaS console with indigo glow that it replaces.

OWN-WORLD: A white sidebar with hairline rules (user-pinned on 2026-10-22, replacing the original bottle-green cloth). The open section is highlighted in an ink-blue tint. Work happens on white pages over a faint green-grey ground. Blue-black ink is the action and focus colour, and red pencil is kept for problems only (absent, debt, errors, delete). Flat fills, one 1px hairline weight for every rule, small paper radii, no gradients or glows. Golos Text throughout, with tabular numerals. The theme is light by default, with a dark "register at night" variant.

STORY: A teacher opens the page, sees their group's marks column, marks each child in seconds and trusts what was saved. A director scans money and staff in the same calm register language.

FIRST VIEWPORT: The white sidebar on the left (a drawer on phones) and a white topbar with search. The panel title is set as a register heading with group and date. A summary line shows marked/total and four mark tallies, then the list of children. Each child row ends in a fixed mark column, and the primary action ("Qolganlarni Keldi qilish") sits sticky at the bottom on phones.

FORM: Class register, my top-ranked grounded candidate (#1), chosen by the user as the pick over the assigned Atlas silk. seed: 67bd50bfc9f43da1. Signature move: every status is a register mark (check, cross, note, clock), drawn in its own ink colour in a fixed mark column. The same marks appear in attendance rows, tally chips, the Tabel grid and dashboard activity. Raises: one hairline weight for every rule (from the centre-rail reference-setting page); flat unmodulated colour with no glow (from the zoo guide map); state carried by mark shape as well as hue (from the emission-line rail).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
