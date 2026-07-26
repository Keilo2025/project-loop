# Design contract

For any project with a user interface. The Architect instantiates this in
`/loop-project/1-spec/design-contract.md` during Phase 1, and the Judge enforces it at check 7.

It is a contract rather than a style guide because the failure it prevents is specific and
expensive: UI that satisfies every functional acceptance criterion and is still obviously
unshippable. That outcome is very cheap to prevent at Phase 1 and very costly to fix at Phase 3,
because by then the wrong decisions are distributed across every screen.

---

## 1. Tokens before pixels

Define the system first; build components against it. Nothing in a component file contains a
literal colour, spacing value, radius, shadow, or font size.

- **Colour.** Semantic names, not literal ones — `surface`, `surface-raised`, `text-primary`,
  `text-muted`, `border`, `accent`, `danger`, `warning`, `success`. Each with the states it needs.
  Naming a token `blue-500` guarantees a redesign becomes a find-and-replace.
- **Type scale.** A fixed ramp with a stated ratio, and a line-height per step. Long-form text sits
  between 60 and 75 characters per line.
- **Spacing scale.** One scale, usually a 4px or 8px base. Every margin and padding is a step on it.
- **Radius, shadow, border.** Small enumerated sets. Two or three of each.
- **Motion.** Duration and easing tokens. One or two durations, not seven.

*Check:* no literal colour, spacing, or font-size values in component source.

---

## 2. Every component covers every state

The most common gap in generated UI is not ugliness — it is a component that renders beautifully
with three rows of ideal data and falls apart with zero rows, or a network error, or a name that
is forty characters long.

Required for each interactive component: **default, hover, focus-visible, active, disabled,
loading, error.**
Required for each data view: **empty, loading, partial, error, populated, overflowing.**

The empty state is a design problem, not a blank div. Say what would be here and how to get there.

*Check:* every state demonstrated — in a story, a fixture, or a screenshot referenced by the QA
report.

---

## 3. Accessibility bar

Target WCAG 2.2 AA unless the DoD states otherwise, and make it blocking. Accessibility treated as
Sev-4 is accessibility that never gets fixed.

- Every interactive element reachable and operable by keyboard alone, in a sensible order
- Focus always visible, and never removed without a stronger replacement
- Contrast measured, not judged by eye: 4.5:1 for body text, 3:1 for large text and for the
  boundaries of interactive components
- Semantic HTML first; ARIA only where semantics genuinely run out
- Every input has a programmatically associated label; errors are linked to their field and
  announced
- Touch targets at least 24×24 CSS pixels, with adequate spacing
- Motion respects `prefers-reduced-motion`
- Nothing communicated by colour alone

*Check:* keyboard-only traversal of each journey, an automated axe-style scan, and measured
contrast values recorded in the QA report.

---

## 4. Responsive floor and ceiling

State the narrowest supported width (360px is the usual floor) and the widest useful width. Layout
adapts at content-driven breakpoints rather than device names. No horizontal scrolling at the
floor. Tables have a stated small-screen strategy — stack, prioritise columns, or scroll within a
labelled region — decided in Phase 1, not improvised per table.

---

## 5. Anti-generic rules

Models converge. Left alone, generated interfaces cluster on a small set of visual clichés that
now read instantly as machine-made. Ban them explicitly, because "make it look good" does not
survive contact with a token budget:

- Purple-to-blue gradient hero with a centred headline and two buttons
- Three equal feature cards in a row, each with an icon above a heading above two lines
- Emoji as interface iconography
- A glassmorphic card floating on a blurred gradient for no reason
- Pill badges reading "AI-Powered", "Blazing Fast", "Enterprise Ready"
- Every corner radius identical and every shadow the same soft grey blur
- Placeholder text left in place of a real empty state

Then state what this product *is*: two or three adjectives with consequences. "Dense and quiet"
implies tight spacing, restrained colour, and typographic hierarchy doing the work. "Warm and
spacious" implies the opposite. An adjective that does not change a decision is decoration.

Pick one genuine anchor — a distinctive typeface pairing, a real accent colour, a consistent
density, a specific illustrative style — and hold it everywhere. Consistency of one strong choice
reads as designed; five weak choices read as generated.

---

## 6. Performance budget

State it as numbers, because "fast" is not checkable. Typical: interaction response under 100ms,
largest contentful paint under 2.5s on the target connection, no layout shift after first paint,
a stated JavaScript budget. Long lists virtualise above a stated row count.

*Check:* measured, with the method and result recorded in the QA report.

---

## 7. Content and copy

Sentence case for headings and buttons. Buttons name the action — "Create project", not "Submit".
Error messages say what happened and what to do next, never an error code alone. Dates and numbers
formatted for the user's locale. Copy is written in Phase 1 alongside the component, not filled in
at the end, because "Lorem ipsum" hides layout problems that real text reveals.

---

## Writing the design contract

Keep it to a page. Sections: tokens, component inventory with required states, accessibility bar,
responsive floor, the two or three adjectives, the anti-generic bans that apply, the performance
budget.

A contract nobody reads is worse than none, because it creates the appearance of a standard. If it
runs past a page, cut the parts that would not change a decision.
