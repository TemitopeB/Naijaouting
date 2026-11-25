---
name: NaijaOuting
description: What's on in Nigeria, checked and linked to the official seller.
colors:
  naija-green: "#0B6B4C"
  naija-green-deep: "#08573D"
  naija-green-tint: "rgba(11,107,76,.09)"
  live-green: "#0B6B4C"
  marigold: "#E9A21B"
  harvest-gold: "#A86F12"
  signal-red: "#D7303B"
  limestone: "#F4F3EF"
  limestone-deep: "#ECEBE6"
  paper: "#FFFFFF"
  paper-warm: "#FAF9F6"
  paper-sunk: "#F0EFEA"
  hairline: "#E8E6E0"
  hairline-strong: "#DAD8D1"
  ink: "#141614"
  ink-muted: "#5C5E58"
  ink-quiet: "#6D6F68"
  night: "#0B0F0D"
  night-panel: "#141A17"
  night-panel-raised: "#18201C"
  night-hairline: "#232B26"
  night-ink: "#F1F4F1"
  night-ink-muted: "#A3ACA6"
  night-green: "#3DBE85"
  night-live: "#4ADE80"
  night-marigold: "#F0B23E"
  night-red: "#FF5B66"
typography:
  headline:
    fontFamily: "'Space Grotesk', 'Noto Sans', system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "'Space Grotesk', 'Noto Sans', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "'Plus Jakarta Sans', 'Noto Sans', system-ui, sans-serif"
    fontSize: "clamp(15px, .85rem + .2vw, 16px)"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'Plus Jakarta Sans', 'Noto Sans', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.06em"
  control:
    fontFamily: "'Plus Jakarta Sans', 'Noto Sans', system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.5
  date-numeral:
    fontFamily: "'IBM Plex Sans', 'Noto Sans', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 800
    lineHeight: 1
rounded:
  nav-item: "14px"
  card-media: "17px"
  panel: "20px"
  card: "24px"
  shell: "30px"
  pill: "999px"
spacing:
  card-inset: "8px"
  chip-x: "13px"
  button-x: "16px"
  grid-gap: "20px"
components:
  button-primary:
    backgroundColor: "{colors.naija-green}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    typography: "{typography.control}"
    padding: "0 16px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.pill}"
    typography: "{typography.control}"
    padding: "0 10px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 13px"
  chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.limestone}"
    rounded: "{rounded.pill}"
    padding: "0 13px"
  event-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.card-inset}"
  event-card-media:
    backgroundColor: "{colors.paper-sunk}"
    rounded: "{rounded.card-media}"
  date-pill:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "6px 10px"
  sidebar:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.shell}"
    padding: "20px 12px 14px"
---

# Design System: NaijaOuting

## Overview

**Creative North Star: "The Honest City Guide"** *(provisional name, chosen during the first documentation pass; rename freely)*

NaijaOuting looks like a calm, well-kept guidebook laid over a busy city. The chrome stays quiet so the event flyers, which are loud, colourful and handmade by organisers, can carry the energy. Surfaces are pale limestone and white paper with soft, short shadows; one confident Naija green marks every action that moves you forward, marigold marks dates and time, and signal red is kept for "live" and warnings.

The system is an **Operate** interface first: a browsing and planning tool used mostly on phones, on mobile data, often opened from a WhatsApp link. Density is medium. Cards are large and picture-first; controls are rounded pills that are easy to hit with a thumb. Trust signals ("Checked", "Official seller", scam warnings, "Venue to be confirmed") are part of the visual language, not footnotes.

The landing page (`/`) shares the app's palette, shapes and shadows but has its own editorial voice, modelled on awwwards.com: a full-width layout with slim side gutters (`clamp(16px, 3.4vw, 56px)`), a near edge-to-edge hero panel, **Space Grotesk** at semi-bold (600) for very large display headings (hero up to 120px, sections up to 64px), Plus Jakarta Sans lead text on large screens, and plain sentence-case labels above headings.

**Key Characteristics:**
- Picture-first event cards: a square flyer or category illustration, then category label, title, date, place.
- One action colour (Naija green) for primary buttons, selected states and links.
- Pills everywhere: chips, buttons, date pills, tags.
- Soft, short shadows on white cards over a pale limestone page.
- Full light and dark themes, plus three alternative modes (Ankara, Lagoon, High contrast) chosen in Settings.

## Colors

A restrained neutral base with one green action colour and two signal colours, mirrored for dark mode.

### Primary
- **Naija Green** (naija-green): primary buttons, selected nav, "Add event", links, the "Checked" badge. In dark mode it lifts to **Night Green** (night-green) so it stays legible on near-black.
- **Deep Naija Green** (naija-green-deep): pressed and hover state of green actions.
- **Green Wash** (naija-green-tint): selected backgrounds and soft success fills.

### Secondary
- **Marigold** (marigold): dates, "this weekend" highlights and the 7-day countdown on event pages. **Harvest Gold** (harvest-gold) is its text-safe darker partner on light surfaces.
- **Live Green** (live-green / night-live): the "On now" dot and status.

### Tertiary
- **Signal Red** (signal-red / night-red): the LIVE news badge, scam warnings, review counts and destructive actions. Use sparingly.

### Neutral
- **Limestone** (limestone): the page background behind cards; **Limestone Deep** (limestone-deep) for wells.
- **Paper** (paper), **Warm Paper** (paper-warm), **Sunk Paper** (paper-sunk): cards, panels, and the empty flyer area.
- **Hairline** (hairline) and **Strong Hairline** (hairline-strong): borders on chips, inputs and dividers.
- **Ink** (ink), **Muted Ink** (ink-muted), **Quiet Ink** (ink-quiet): primary text, secondary text, captions.
- **Night** family (night, night-panel, night-panel-raised, night-hairline, night-ink, night-ink-muted): the dark theme's equivalents.

### Named Rules
**The One Action Colour Rule.** Only Naija Green says "do this". Marigold is for time, red is for danger or live. Never make a primary button marigold or red.

**The Flyer Is Loudest Rule.** Organisers' flyers are full of colour; the interface around them stays neutral so they never compete.

## Typography

Four self-hosted families, each with one job. Files live in `/fonts/` (variable woff2, trimmed to the weights below, split into latin / latin-ext / vietnamese subsets); `fonts/type-v1.css` holds the `@font-face` rules and the tokens. Pages link that stylesheet and preload only the Plus Jakarta Sans and Space Grotesk latin files.

**Display:** Space Grotesk 400–700 (`--font-display`, aliased as `--fd`): page and section headings, event and place titles, featured and promo headings, landing headlines.
**Interface:** Plus Jakarta Sans 400–800 (`--font-interface`, aliased as `--fb` and `--fm`): body, navigation, buttons, chips, inputs, dropdowns, labels, descriptions, footer, admin.
**Numbers:** IBM Plex Sans 400–700 (`--font-numbers`, aliased as `--fn`, utility class `.tnum`): prices, currency, dates and times, date tiles, counts, statistics, distances. Always with `font-variant-numeric: tabular-nums`.
**Fallback:** a Noto Sans subset (`--font-fallback` begins with it) covering only what the three families lack: Hausa hooked letters (Ɓ ɓ Ɗ ɗ Ƙ ƙ Ƴ ƴ), ǹ, combining tone marks, Latin Extended Additional, Vietnamese and the whole currency block. After it come metric-matched local fallbacks (Arial / Liberation Sans with size-adjust and ascent/descent overrides, so text barely moves when the web font arrives), then system fonts, symbol fonts and emoji.
**Wordmark:** Bricolage Grotesque, reserved for the hidden NaijaOuting wordmark (`--fw`).

**Character:** a confident, slightly technical grotesk on top, a warm friendly sans underneath, and a precise plex for anything you count or pay. Tight negative tracking on headlines, open tracking on small uppercase labels.

### Scale (tokens in `type-v1.css`)
- `--fs-hero` 36→56px, `--fs-h1` 30→40px, `--fs-h2` 24→28px, `--fs-title` 18→20px, `--fs-card` 17→18px, `--fs-body` 15→16px, `--fs-sm` 13→14px, `--fs-xs` 12px, `--fs-price` 18→20px, `--fs-nav` 14px, all fluid with `clamp()`.
- Event and place page titles: `clamp(26px, 1.2rem + 1.25vw, 36px)`; drawer section titles use `--fs-h2`.
- Card titles, chips, controls and card price lines keep their existing sizes so card heights and the grid don't change. The landing hero keeps its own larger clamp (up to 120px).
- Weights: `--wt-regular` 400, `--wt-medium` 500, `--wt-semibold` 600, `--wt-bold` 700, `--wt-heavy` 800. Plus Jakarta Sans has no 300, so "light" text renders at 400.

### Named Rules
**The Role Not Element Rule.** Pick the font by what the text is, not where it sits: a price inside a heading still uses `--font-numbers`. Never write a font name directly in a component; use the four tokens.

## Layout

- **Computer (901px and wider):** a floating white sidebar (Discover / More groups, Add event, Settings, account and help links) on the left; the main column holds a top bar (news ticker, theme toggle, account, Review), a filter panel, then a card grid using `repeat(auto-fill, minmax(264px, 1fr))` with a 20px gap. Map, Near me, Tourism and Explore use a two-column split: map on the left, a 360–420px list on the right.
- **Phone (760px and narrower, with refinements at 600, 420 and 380px):** a bottom tab bar (Events, Map, Near me, Saved, More), a compact header with search and Add event, a List/Calendar switch, a horizontally scrolling chip row, and one card per row. The map sits on top with the list below.
- Event details open as a right-hand drawer on computers and a full-screen sheet on phones, with a sticky action bar (Directions, Save, Share).
- Rhythm is loose and even: an 8px inset inside cards, 12–20px between controls, 20px between cards.

## Elevation & Depth

Depth is soft and shallow: white surfaces lift off the limestone page with short, low-opacity shadows; there are no hard borders on cards. Buttons carry a slight inner hairline and a tiny drop to feel pressable. Dark mode uses the same structure with stronger, darker shadows.

### Shadow Vocabulary
- **Resting card** (`0 1px 2px rgba(24,28,26,.04), 0 6px 18px -8px rgba(24,28,26,.12)`): event cards and panels.
- **Floating shell** (`0 2px 6px rgba(24,28,26,.05), 0 18px 40px -16px rgba(24,28,26,.20)`): the sidebar and drawers.
- **Pressable** (`0 1px 2px rgba(24,28,26,.06), 0 4px 12px -4px rgba(24,28,26,.10), inset 0 0 0 1px rgba(24,28,26,.05)`): buttons and nav items.
- **Primary lift** (`0 1px 2px rgba(6,40,28,.22), 0 8px 20px -10px rgba(11,107,76,.65)`): the green primary button.

### Named Rules
**The Short Shadow Rule.** Shadows are for lifting paper off stone, never for glow. Avoid coloured halos, especially in dark mode.

## Shapes

Generously rounded, friendly geometry. The outer shell is the roundest (30px), cards are 24px with their media inset at 17px so the corners nest, panels are 20px, nav items 14px, and every control is a full pill (999px). Square flyer frames (1:1) are the signature silhouette of the Events grid.

## Components

### Buttons
- **Shape:** full pill (999px), 40px tall in toolbars.
- **Primary:** Naija Green fill with white text and the Primary lift shadow; used for Add event, Directions, Approve, Find events.
- **Secondary:** white or transparent with Muted Ink text and the Pressable shadow; used for Save, Share, Open, Edit first.
- **Hover / Focus:** darker green on hover; visible focus ring for keyboard users.

### Chips
- **Style:** white pill with a hairline border, 13px Control text.
- **State:** selected chips invert to Ink fill with Limestone text (for example "Upcoming", "All events"). Filter chips include Online and webinars, Free entry, Verified only.

### Cards / Containers
- **Event card:** white, 24px corners, 8px inset, Resting card shadow. Square media area (flyer, darkened slightly on computers until hover; or a category illustration), a "Today"/"On now" tag top-left, save heart top-right, a date pill bottom-left. Below: uppercase category label, title, date line, place line with a pin, and an optional fee/registration tag.
- **Panels:** Review sections, filter panel and event facts use white or warm paper with 20px corners.

### Inputs / Fields
- **Style:** pill search field with an icon; form fields in the Add event modal are rounded rectangles with hairline borders.
- **Focus:** green ring.

### Navigation
- **Computer:** floating sidebar with grouped links, counts on the right (Events 200, News 24), the current page as a raised white pill.
- **Phone:** bottom tab bar with icon and label; the current tab gets a green tint.

### Event Drawer (signature)
A tall flyer header with the countdown date block, a "Checked" badge, title, status line ("On now · until 22 Nov"), a facts card (date with Add to calendar, venue with Map), the description, and a sticky bar with a full-width green Directions button beside Save and Share.

## Do's and Don'ts

### Do:
- **Do** keep Naija Green as the only action colour and give each screen one clear primary action.
- **Do** show unknown details honestly ("Venue to be confirmed", "See organiser") in Muted Ink rather than hiding the field.
- **Do** keep flyers in square frames and let them be the most colourful thing on the screen.
- **Do** check every change in light mode, dark mode and on a 390px-wide phone.

### Don't:
- **Don't** add coloured glow shadows; use the neutral shadow vocabulary.
- **Don't** add font families beyond the four in `fonts/type-v1.css`, or write font names directly in components.
- **Don't** show the NaijaOuting logo or wordmark until the owner asks for it back, and don't use third-party logos from the internet.
- **Don't** show invented counts, testimonials, ratings or partner logos.
- **Don't** box the landing page into a narrow centred column; it runs full width with slim gutters.
- **Do** keep landing page containers white with a visible edge (#CFCDC4) and a layered shadow, on beige (#EEEDE8) or deeper beige (#E3E1D9) bands, never white on white. Marigold (#E9A21B) is the one bold band, for Detty December.

## Events app v2 (18 Nov 2026)

- Headings use the display token (`--fd`, now Space Grotesk), body the interface token (now Plus Jakarta Sans); see Typography.
- Event cards: picture badge carries the start date; the line under the title carries only what the badge can't: "Until <end>" for multi-day events, a short start time, and the entry price (green when free). No price known: "Entry details: see organiser". The pin line shows "Venue, City" when the venue name is short.
- Phones: 4:3 card pictures; search is a full search bar in the header, "+ Add" is a small outline button.
- Computers: four columns from about 1280px; filters in one row (search, category, city, "More filters" sheet, Sort menu).
- Category covers repeat less: four variants per category (as is, mirrored, and two zoomed crops, nudged at most 6%).
- News strip label is neutral with a small red dot; events lead the page.
- Sidebar Settings is a plain link. Source badge reads "From a listing site" instead of "Listed".
