---
name: Bog'chaOS
description: Staff dashboard for private kindergartens, drawn as the school class register (sinf jurnali)
colors:
  register-ink: "#1f3c96"
  register-ink-deep: "#182f78"
  ink-tint: "#e4e9f5"
  red-pencil: "#c0262d"
  red-pencil-tint: "#fae4e4"
  mark-present: "#1c7a4a"
  mark-present-tint: "#e2f0e7"
  mark-excused: "#9a5800"
  mark-excused-tint: "#f8ecd6"
  mark-late: "#6a3d9a"
  mark-late-tint: "#eee6f6"
  green-grey-ground: "#f1f3ef"
  page-white: "#ffffff"
  page-hover: "#f7f8f5"
  page-surface: "#eceee9"
  hairline: "#d8ddd5"
  hairline-strong: "#a8b0a5"
  blue-black-ink: "#1a1f2b"
  ink-secondary: "#485160"
  ink-muted: "#5b6370"
  night-ground: "#0f1411"
  night-page: "#171e1a"
  night-sidebar: "#151b17"
  night-surface: "#202925"
  night-hairline: "#2b3530"
  night-ink: "#e8ece7"
  night-ink-line: "#9db2f2"
  night-ink-fill: "#2c4aa8"
typography:
  display:
    fontFamily: "Golos Text, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Golos Text, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(1.2rem, 1.5vw, 1.5rem)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  title:
    fontFamily: "Golos Text, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.3
    fontFeature: "tnum"
  body:
    fontFamily: "Golos Text, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "Golos Text, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 600
    lineHeight: 1.4
    fontFeature: "tnum"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.register-ink}"
    textColor: "{colors.page-white}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.register-ink-deep}"
  button-secondary:
    backgroundColor: "{colors.page-white}"
    textColor: "{colors.blue-black-ink}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.page-surface}"
  button-danger:
    backgroundColor: "{colors.page-white}"
    textColor: "{colors.red-pencil}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
  button-danger-hover:
    backgroundColor: "{colors.red-pencil-tint}"
  input-default:
    backgroundColor: "{colors.page-white}"
    textColor: "{colors.blue-black-ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "40px"
  card:
    backgroundColor: "{colors.page-white}"
    rounded: "{rounded.lg}"
    padding: "24px"
  nav-item:
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
    height: "44px"
  nav-item-active:
    backgroundColor: "{colors.ink-tint}"
    textColor: "{colors.register-ink}"
  badge-present:
    backgroundColor: "{colors.mark-present-tint}"
    textColor: "{colors.mark-present}"
    rounded: "{rounded.full}"
    padding: "3px 10px"
  badge-problem:
    backgroundColor: "{colors.red-pencil-tint}"
    textColor: "{colors.red-pencil}"
    rounded: "{rounded.full}"
    padding: "3px 10px"
  attendance-button:
    backgroundColor: "{colors.page-surface}"
    textColor: "{colors.blue-black-ink}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
    height: "48px"
  attendance-button-present:
    backgroundColor: "{colors.mark-present}"
    textColor: "{colors.page-white}"
  attendance-button-absent:
    backgroundColor: "{colors.red-pencil}"
    textColor: "{colors.page-white}"
  attendance-button-excused:
    backgroundColor: "{colors.mark-excused}"
    textColor: "{colors.page-white}"
  attendance-button-late:
    backgroundColor: "{colors.mark-late}"
    textColor: "{colors.page-white}"
---

# Design System: Bog'chaOS

## Overview

**Creative North Star: "The Class Register"**

Bog'chaOS is drawn as the sinf jurnali every teacher already keeps: white pages laid over a faint green-grey ground, one hairline weight for every ruled line, blue-black ink for anything you act on, and a red pencil that only comes out for problems. The sidebar is a plain white page with hairline rules (user-pinned, replacing the earlier bottle-green cloth cover); the open section is picked out in a pale ink-blue tint. Nothing glows, nothing has a gradient, and nothing lifts on hover.

The signature is the register mark. Every attendance status is a drawn mark (check, cross, note, clock) from one SVG symbol sprite, each in its own ink colour, always in a fixed mark column. The same marks recur in attendance rows, tally chips, the monthly tabel grid and the dashboard activity feed, so state is carried by shape as well as hue.

Density is calm and operational: teachers mark a group in seconds on a phone in daylight, directors read money and staff at a desk in the same register language. Light is the default; a dark "register at night" variant swaps the pages for deep green-black sheets while solid ink fills stay deep enough to carry white labels.

**Key Characteristics:**
- Golos Text everywhere, tabular numerals on by default at the body level.
- Light default on a green-grey ground (`data-theme="light"`), full dark override via `[data-theme="dark"]`.
- One action ink, one problem pencil, four status marks; no decorative colour.
- 1px hairlines for every rule, small paper radii, flat unmodulated fills.
- Summary figures read as one ruled line, not separate stat tiles.

## Colors

A paper-and-ink palette: neutral green-greys for the page, one blue-black ink for action, and a small set of mark inks that each mean exactly one thing.

### Primary
- **Register Ink** (#1f3c96): the action and focus colour. Solid fills (primary button, active filter tab, logo block) use `--fill-primary`; text, links, chart bars, focus rings and today markers use `--color-primary`. In light theme both resolve to this ink.
- **Register Ink Deep** (#182f78): hover for ink fills and ink text.
- **Ink Tint** (#e4e9f5): the active nav item, avatar grounds, today's tabel column, info alerts, selection.
- **Night Ink Line** (#9db2f2) and **Night Ink Fill** (#2c4aa8): in the dark variant, line/text ink lightens to #9db2f2 for contrast, while solid fills stay deep at #2c4aa8 so white labels still pass.

### Secondary
- **Red Pencil** (#c0262d) on **Red Pencil Tint** (#fae4e4): absent, debt, errors, critical stock, delete, the notification count. Never decoration.

### Tertiary
- **Present Green** (#1c7a4a, tint #e2f0e7): present mark, paid, positive trend, group fill bars, live indicators.
- **Excused Ochre** (#9a5800, tint #f8ecd6): excused mark, pending, warnings, the demo-data chip.
- **Late Violet** (#6a3d9a, tint #eee6f6): late mark only.

### Neutral
- **Green-Grey Ground** (#f1f3ef): the app background the pages sit on.
- **Page White** (#ffffff): cards, sidebar, topbar, inputs.
- **Page Hover** (#f7f8f5) and **Page Surface** (#eceee9): row hover; table heads, icon buttons, unpressed attendance buttons, modal footers, weekend columns.
- **Hairline** (#d8ddd5): every ruled line, card edge and divider. **Hairline Strong** (#a8b0a5): input and secondary-button strokes, table-head underline.
- **Blue-Black Ink** (#1a1f2b), **Ink Secondary** (#485160), **Ink Muted** (#5b6370): text, three steps.
- **Night set**: ground #0f1411, sidebar #151b17, page #171e1a, surface #202925, hairline #2b3530, ink #e8ece7. Night status inks lighten (present #5cc794, excused #e6a84a, absent #f07479, late #c2a0ea) and their tints become 14% washes.

### Named Rules
**The Red Pencil Rule.** Red (#c0262d) appears only where something is wrong: absent, debt, error, critical, delete. A red element that is not a problem is a bug.

**The One Ink Rule.** Register Ink is the only action and focus hue. Present green, excused ochre and late violet are mark inks, not accents.

**The Deep Fill Rule.** Solid fills that carry white text (primary button, pressed attendance buttons) stay deep in both themes: `--fill-primary` for ink, `--att-present/absent/excused/late` for marks. Light text-ink variants are never used as fills.

## Typography

**Display Font:** Golos Text (with -apple-system, Segoe UI, Roboto, sans-serif)
**Body Font:** Golos Text
**Label/Mono Font:** Golos Text (codes and document numbers too, with tabular numerals)

**Character:** One humanist grotesque that renders Uzbek Latin and Cyrillic names equally well, used at a few weights; hierarchy comes from size and weight, never from a second family.

### Hierarchy
- **Display** (700, 1.6rem, 1.2; 1.45rem under 768px): panel titles, set as the register heading.
- **Headline** (700, clamp(1.2rem, 1.5vw, 1.5rem)): summary-line figures; the attendance progress count is 1.5rem.
- **Title** (700, 1.15rem, 1.3): card titles; modal titles 1.2rem; child names in attendance 1rem.
- **Body** (400-500, 0.85-0.92rem, 1.5): tables (0.88rem), forms (0.9rem), descriptions; panel subtitles cap at 68ch. Inputs go to 16px on phones.
- **Label** (600, 0.75-0.85rem): table heads, field labels, stat labels, badges and tallies. Sentence case.

### Named Rules
**The Tabular Ledger Rule.** `font-variant-numeric: tabular-nums` is set on body; every count, sum, time and date column aligns like a ledger.

**The Loaded Weights Rule.** Golos Text is loaded at 400, 500, 600 and 700. Use only those.

## Layout

A fixed 264px white sidebar with a hairline right edge sits beside a 64px sticky white topbar and a 32px-padded content area (20px 16px on phones). Below 1024px the sidebar becomes a drawer (min(300px, 86vw)) over a 55% scrim, opened by a 44px menu button.

Breakpoints: 640px (attendance controls go two-column), 768px (topbar clock and role switcher hide, header actions stack, inputs 16px), 1024px (sidebar fixed, desktop register).

Spacing steps on 4px: 4, 8, 12, 16, 20, 24, 28, 32. Panel header to content is 28px; card padding 24px; grid gaps 16-24px.

The summary line is one ruled card divided by 1px vertical hairlines into auto-fit columns (min 200px), not separate tiles. Attendance on desktop is a single ruled register: one grid row per child (avatar 36px, name, sync state, four choices, a 40px mark column), hairlines between rows. On phones each child is a card with a 2x2 grid of 48px mark buttons, and the bulk action ("Qolganlarni Keldi qilish", 52px) sits in a sticky bar at the bottom. Wide tables scroll inside their card, capped to the viewport, with sticky head, name column and actions column.

## Elevation & Depth

The system is flat. Depth comes from page-on-ground contrast and hairlines, not shadow. Cards, rows and controls carry no shadow at rest or on hover. Shadows exist only for things that genuinely float above the page.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 16px 40px rgba(26, 31, 43, 0.18)`; night 0.55 black): modals and the phone drawer.
- **Lift** (`box-shadow: 0 2px 8px rgba(26, 31, 43, 0.08)`): the login card only.
- **Rest** (`box-shadow: 0 1px 2px rgba(26, 31, 43, 0.06)`; none at night): the active login tab only.
- **Toast** (`box-shadow: 0 8px 24px rgba(26, 31, 43, 0.25)`): dark ink toasts.

### Named Rules
**The No Glow Rule.** No gradients, glows, coloured shadows or hover lifts. Hover changes fill or stroke, never position.

**The One Hairline Rule.** Every rule, border and divider is 1px. Emphasis comes from the stronger hairline colour (#a8b0a5) or a status colour, not a thicker line. (The 2-3px undo-countdown bar and today's 2px inset underline are progress and position indicators, not rules.)

## Shapes

Small paper radii: 4px for tabs, tabel cells and toast actions; 6px for buttons, inputs, nav items, group and stock cards; 8px for main cards, the attendance register and the summary line; 12px for modals and the login card. Full pills are reserved for badges, tallies, chips and the topbar search. Circles mark people (avatars) and register marks. Empty mark slots are a dashed hairline circle waiting for ink.

## Components

### Buttons
Plain, confident, ink-on-paper.
- **Shape:** gently squared (6px), min 40px tall (44px on phones), 32px for the small size.
- **Primary:** solid Register Ink fill, white label, 600 weight, 9px 18px.
- **Hover / Focus:** fill deepens to #182f78; focus is a 2px ink outline offset 2px. No movement.
- **Secondary:** white page with a strong hairline, ink text; hovers to Page Surface.
- **Danger:** white with red-pencil text and a red hairline; hovers to the red tint.
- **Success:** solid present green with white label (dark label at night).

### Chips
- **Style:** full pill, 3px 10px, 0.75rem 600, status ink on its own tint (present, excused, absent, info).
- **Tallies:** the same pill carrying the register mark and a tabular count, one per status.

### Cards / Containers
- **Corner Style:** 8px (6px for small grid cards).
- **Background:** Page White on the ground.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px Hairline.
- **Internal Padding:** 24px; ruled headers 20px 24px with a hairline beneath.

### Inputs / Fields
- **Style:** white, 1px strong hairline, 6px, 40px (48px in attendance controls).
- **Focus:** border turns Register Ink plus a 2px Ink Tint outline.
- **Labels:** 0.82-0.85rem 600 secondary ink above the field.

### Navigation
- **Style:** white sidebar, 0.92rem 500 secondary ink, 44px rows, 6px radius, section groups separated by hairlines.
- **Hover:** green-grey fill, full ink text. **Active:** Ink Tint fill, Register Ink text, 600.
- **Mobile:** the same page as a slide-in drawer.

### Register Marks (signature)
Four SVG symbols in one sprite (`#mark-PRESENT` check, `#mark-ABSENT` cross, `#mark-EXCUSED` note, `#mark-LATE` clock), drawn as 2.4 round strokes in `currentColor` at 1em. They are the only status iconography: in the attendance mark column (filled tint circle, 36-40px), inside attendance buttons, tally chips, tabel cells and the activity feed.

### Attendance Register (signature)
Phone: one card per child with a 2x2 grid of 48px buttons; the pressed button fills with its deep mark colour and white label; the card edge picks up a 40% mix of the status colour; a 3px ink bar drains across the bottom during the undo window. Desktop (1024px+): the cards collapse into one ruled register with the mark column fixed at the right edge and 38px buttons.

## Do's and Don'ts

### Do:
- **Do** use the custom properties (`--bg-*`, `--text-*`, `--color-*`, `--fill-*`, `--radius-*`) so both themes stay live.
- **Do** draw every status with the sprite mark plus its colour; shape and hue together.
- **Do** use `--fill-primary` for solid ink fills and `--color-primary` for ink text and lines.
- **Do** keep every rule at 1px and every card on Page White with a Hairline edge.
- **Do** print values outright (chart percentages are always shown); touch screens have no hover.
- **Do** keep phone attendance targets at 48px and the bulk action sticky at the bottom.

### Don't:
- **Don't** use red (#c0262d) for anything that is not a problem.
- **Don't** add gradients, glows, coloured shadows or hover lifts.
- **Don't** split summary figures into separate stat tiles; keep the ruled summary line.
- **Don't** introduce a second display family, emoji or glyph icons for status; the register marks are the status vocabulary.
- **Don't** use uppercase tracked labels above titles; labels stay sentence case.
- **Don't** bring the register chrome into the Telegram Mini App simulator; it deliberately uses Telegram's own palette and system font.
