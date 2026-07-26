# Content contract

For any project that ships words a user reads. The Content Strategist instantiates this in
`/loop-project/1-spec/content-contract.md` during Phase 1; when that role is off, the Designer's
copy section covers it thinly. The Tester checks the string table and the UI Critic checks the
register.

The failure it prevents: twelve components written by four Workers in four voices, none of them the
product's, plus a marketing surface that reads as machine-generated to the exact audience it was meant
to persuade. Both are cheap to prevent here and expensive to fix later, because by then the wrong
voice is distributed across every screen.

**The rule that makes this work: ship the strings, not guidance about strings.** "Use clear, friendly
microcopy" produces inconsistency. A table of the actual headings, labels, empty states and errors
produces one voice and stops the Worker guessing.

---

## 1. Message hierarchy

Top down, in priority order.

- **One sentence** on what this is and who it is for — in the language the audience uses about itself,
  not the language the company uses about the product. If the sentence would fit any competitor, it
  says nothing.
- **Three claims**, ranked, each with the evidence it rests on. A claim with no evidence is one the
  Judge cannot let ship and a reader will not believe. If the evidence does not exist, cut the claim
  and record why.
- **The objection you are answering.** Every audience arrives with a specific reason to not bother.
  Name it and say where the content addresses it.

---

## 2. Voice, stated as bans

Adjectives do not constrain a generator. Bans do.

Write the rules as a table of *never* and *always*: whether contractions are allowed, whether second
person is used, sentence case or title case, whether exclamation marks appear at all, maximum sentence
length, whether questions may be used as headings.

Then **ban the generated register explicitly and by example**, because this is the section that most
changes the output:

| Banned | Why |
|---|---|
| "unlock", "elevate", "supercharge", "revolutionise", "seamless", "effortless", "game-changing", "robust" | The house style of every model. Instantly recognisable, and it makes true claims read as false. |
| "In today's fast-paced world", "Gone are the days of", "Let's dive in" | Openers that carry no information and signal generation. |
| "It's not just X — it's Y" | The single most identifiable AI sentence pattern. |
| Rule-of-three lists in every paragraph | Cadence that reads as filler once noticed. |
| Heading followed by a subheading restating it | Doubles the word count and adds nothing. |
| Em-dash-heavy prose that circles the point before making it | Reads as hedging. Say the thing. |
| "Whether you're a X or a Y" | Audience-flattering non-specificity. |
| Closing paragraphs that summarise what was just said | The reader was there. |

*Check:* the UI Critic greps the shipped strings for the banned list and reads three surfaces for
register. A hit is a Sev-3; placeholder text still in place is a Sev-2.

---

## 3. Interface copy, as a table of real strings

| Surface | String | Constraint |
|---|---|---|
| Primary CTA, dashboard | `Create project` | Names the action. ≤ 20 chars. |
| Empty state, project list | `No projects yet. Create one to start tracking work.` | Says what would be here and how to get there. ≤ 90 chars. |
| Error, expired session | `Your session expired. Sign in again — your draft is saved.` | What happened, then what to do. Never an error code alone. |

Rules that hold across the table:

- **Buttons name the action.** "Create project", not "Submit". Not "OK" where a verb exists.
- **Errors say what happened and what to do next.** A code with no next step is a dead end.
- **Empty states say what would be here and how to get there.** A blank div is a design failure
  wearing a content failure.
- **Character ceilings where the layout has one.** Copy that overflows is a layout bug filed against
  working code, and the Worker cannot guess the ceiling.
- **Dates, numbers, currencies formatted for the user's locale**, with the format named.
- **No placeholder text ships.** "Lorem ipsum" hides layout problems real text reveals.

---

## 4. Terminology, anchored

A two-column table: the approved term, and the terms it replaces. Where `0-plan/domain.md` exists its
vocabulary table is **authoritative** — contradicting it puts two vocabularies in one product, and the
one in the code usually wins by accident.

Name a reading level and the tool that measures it. "Plain English" is not checkable; "Flesch–Kincaid
grade 9 or below, measured with X" is.

---

## 5. Structure for retrieval, without writing for machines

Where the SEO or LLM Specialist roles are enabled, they will require content shapes. Fill them, but
**write for the human reader first** — content optimised for a retrieval system and not a person fails
both, because the systems now measure engagement too.

The shapes that serve both:

- **The answer near the question**, not after three paragraphs of preamble
- **Passages that survive being quoted alone** — no "as mentioned above", no pronoun whose referent is
  two paragraphs back, entities named in full at least once per section
- **Facts with figures and dates attached**, and a source named for each. This is the intervention
  with the strongest published effect on citation, and it is also just better writing.
- **A definition near the term it defines**
- **Genuine question-and-answer blocks** where real questions exist — not invented ones manufactured to
  fill a schema

*Check:* pick three passages at random and read them out of context. If any is unintelligible or
misleading alone, it fails.

---

## 6. Claims discipline

Every factual or comparative claim in shipped copy gets a source in this contract, or it does not
ship. Superlatives about the product require evidence in the same way any other claim does. Where the
vertical regulates claims — health, finance, environmental, employment — the domain brief will say so,
and the constraint is a hard one, not a tone preference.

**No fabricated social proof.** No invented testimonials, no placeholder logos, no "trusted by
thousands" without a number you can defend. This is a Sev-1, not a copy note.

---

## Writing the content contract

Keep it to two pages plus the string table, which is as long as it needs to be. Sections: message
hierarchy, voice bans, string table, terminology, retrieval structure, claims discipline.

The string table is the deliverable. Everything above it exists to make the table consistent, and a
contract with excellent principles and no strings will be ignored by every Worker who needs a button
label at 2am.
