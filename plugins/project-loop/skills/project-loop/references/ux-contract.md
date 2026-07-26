# UX contract

For any project whose users are not the person building it. The UX Researcher instantiates this in
`/loop-project/1-spec/ux-contract.md` during Phase 1; when that role is off, the Designer absorbs it.
The Tester checks the stated bars and the UI Critic checks the experience as built.

It is a contract rather than a research report because the failure it prevents is specific: a build
that passes every functional acceptance criterion and that the intended user abandons on the second
attempt. Nothing in a functional requirement can catch that, which is why it needs its own gate.

**The division of labour.** This contract owns *behaviour* — what the user is trying to do, how many
steps it takes, what happens when it goes wrong. `design-contract.md` owns *appearance* — tokens,
states, contrast, density. `content-contract.md` owns *wording*. The test for which file a rule
belongs in: would it still hold if the entire visual language changed? If yes, it is a UX rule.

---

## 1. The segment, stated as consequences

A segment is only worth naming if it changes a decision. "Small business owners" changes nothing.
Name the context of use and then write down what follows from it:

| Dimension | Why it changes the build |
|---|---|
| **Device and input** | Thumb on a phone in daylight is a different target size and a different form length from a mouse at a desk. |
| **Session shape** | Two minutes standing up, or forty minutes seated. Determines whether partial progress must persist. |
| **Interruption tolerance** | If the session gets interrupted, does the work survive? For most real jobs the answer must be yes. |
| **Error cost** | A mistyped search is free. A mis-posted journal entry, a wrong dosage, a wrong tenant charged is not. High error cost buys confirmation steps and undo; low error cost does not. |
| **Expertise and frequency** | A daily expert wants density and keyboard shortcuts. A once-a-year user wants guidance. Optimising for the wrong one is the most common UX failure in internal tools. |
| **Environment** | Noisy, gloved, one-handed, offline, shared screen, overlooked by the public. Each rules something out. |

*Check:* every row above answered, and at least three of the answers traceable to a specific rule
elsewhere in this contract. A segment description that produced no rules was decoration.

---

## 2. Jobs, not features

For each primary job, four lines: the **trigger** that starts it, the **outcome** the user wants,
what **"done" looks like to them**, and **what they do today instead**.

That last line is the most useful one in the document. It tells you what you are actually competing
with — usually a spreadsheet, a WhatsApp group, or a colleague who knows — and what the switching
cost has to beat. A build that is better than nothing and worse than the spreadsheet loses.

*Check:* every job traces to at least one business requirement, and every primary journey in section
3 traces to a job.

---

## 3. Journeys with a measurable completion bar

For each critical journey, state the steps and then attach numbers. "Intuitive" is not checkable.
These are:

- **Maximum steps** to complete, counted as screens or committed actions
- **Maximum required fields**, and for each, whether the user has that information to hand at that
  moment — the most common cause of abandonment is a required field the user has to go and find
- **What must persist** across an interruption, a refresh, a lost connection, a session expiry
- **What must be recoverable** — and how, within how long, by whom
- **Time-to-first-value** for a new user: what they must see working before they invest more
- **The primary action's reachability** at the responsive floor, without scrolling

State the bar as a number even when the number is a judgement. A stated bar can be argued with and
tested; an implied one cannot.

*Check:* Tester walks each journey and records step count, field count and outcome against the bar.

---

## 4. Failure states drawn from reality

Not imagined failures — the ones this segment actually hits. The list is short and specific:

- Session expired mid-form
- Offline, or connection dropped between submit and response
- Duplicate submitted because the first attempt looked like it failed
- Wrong record opened, and the user does not notice for three steps
- Data that arrives incomplete, late, or contradicting what is on screen
- Input the field did not anticipate: a very long name, no surname, a name with no spaces, a
  non-Latin script, a value at the exact boundary
- Permission denied for something the UI offered
- Concurrent edit by a colleague on the same record

For each: what the system does, what the user sees, and what they can do next. **A failure state with
no stated recovery is a defect specified in advance.**

*Check:* each listed failure reproduced by the Tester, with the actual behaviour recorded.

---

## 5. Cognitive load rules

The generated-UI failure mode here is symmetrical and both halves are common: either everything is on
one screen because the model had no reason to hide anything, or the flow is split into nine steps
because splitting looked thorough.

Decide and write down:

- What is visible by default versus behind an interaction, and on what basis
- Which decisions have a safe default, so the user can proceed without deciding
- Where progressive disclosure applies, and where it is actively wrong — hiding something a daily
  user needs every time is not simplification
- Whether the primary action on each screen is singular and unambiguous
- What the system remembers so the user does not have to re-enter it

---

## 6. Accessibility as usability, not compliance

`design-contract.md` owns the measurable accessibility bar — contrast, focus, targets, WCAG level.
This contract owns the part a checklist misses: whether each journey is **completable** by keyboard
only, by screen reader, at 200% zoom, with reduced motion, and one-handed. Completable, not merely
technically navigable. An axe scan passes on interfaces nobody can actually use.

*Check:* one full journey completed by keyboard alone and one with a screen reader, recorded in the
QA report as a pass or a specific failure point.

---

## 7. What this product deliberately does not do for the user

Non-goals, in experience terms. Which workflows are out of scope, which user types are explicitly not
served in this cycle, what the product will not automate on the user's behalf. Written down, these
stop Phase 2 from quietly widening scope in the name of helpfulness — which is how a two-week build
becomes a six-week one with no requirement ever having changed.

---

## 8. Evidence and honesty

For every claim about how this segment behaves, name the source: prior art examined, the human's own
account of their customers, published research, support transcripts, an existing analytics view.
Where you had nothing, write **assumed** and state what would test it.

This is the section that decides whether the document is worth anything. An invented persona stated
with the confidence of research is worse than no research, because the Planner builds on it and
nobody knows which parts were fiction.

---

## Writing the UX contract

Keep it to two pages. Sections: the segment and its consequences, jobs, journeys with bars, failure
states, cognitive load rules, accessibility completability, non-goals, evidence.

Cut anything that would not change a build decision or fail a test. A UX contract that reads like a
research deliverable is one the Architect will skim and no Worker will open.
