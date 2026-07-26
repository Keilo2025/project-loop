# Discoverability contract

A menu, not a checklist to paste. Two roles select from it:

- The **SEO Specialist** writes `/loop-project/1-spec/seo-contract.md` from Part A.
- The **LLM Specialist** writes `/loop-project/1-spec/ai-readiness.md` from Part B.

When both roles are off, none of this is written — no other role absorbs it, because no other role
owns it. That is the honest trade: disabling these means the rules are absent, not delegated.

Selected rules are **blocking** unless marked advisory: a Judge returns `REWORK` on failure. Every
rule you select needs a **stated check** — the command, the test, or the manual procedure that proves
it holds. A rule without a check cannot be judged and will not be enforced.

---

## The two things to get right before writing either contract

**1. This is the fastest-moving area in the framework. Verify, do not recall.** Thresholds change,
crawler directives get deprecated, rich-result requirements are revised, and the advice ecosystem is
saturated with confident claims that stopped being true. Search for the current state of anything you
are about to make blocking, and record what you verified and when. Every factual line below carries
its date for exactly this reason.

**2. Specify what engineering controls, and say so.** Rankings and citations are not in your gift.
What you can contract for is that the product is crawlable, indexable, correctly described, fast,
structurally sound, and usable by software. Implying more makes the contract unfalsifiable, and an
unfalsifiable contract cannot be judged.

---

# Part A — Search (SEO Specialist)

Ordered by consequence. The first three are architectural: cheap now, expensive after every page
ships.

**SEO-01 Rendering.** Primary content and primary links exist in the initial HTML response for every
indexable route. Client-only rendering of indexable content is the most common structural SEO defect
in agent-built applications and it passes every functional test.
*Check:* fetch each indexable route template with JavaScript disabled — or `curl` it — and assert the
main content and internal links are present.

**SEO-02 Indexation control, per route pattern.** State explicitly what is indexable and what is not.
`noindex` on thin, duplicate, paginated, faceted, search-result, staging and authenticated surfaces.
`robots.txt` consistent with it. A staging environment indexed by accident is a real, recurring, and
embarrassing incident.
*Check:* a test asserting the robots directive per route pattern, and that non-production hosts are
blocked at the environment level, not only by a meta tag.

**SEO-03 URLs and canonicals.** Stable, lowercase, hyphenated, human-readable. No session state,
tracking parameters or internal ids in the path where a slug would do. One self-referencing canonical
per piece of content. Trailing-slash, protocol and host policy decided once here, with a single
301 hop to the canonical form — never a chain.
*Check:* assert canonical presence and correctness per template; assert the redirect policy resolves
in one hop for each variant form.

**SEO-04 Metadata ownership.** Title and description generated per template from a named source field,
with a stated length ceiling and a stated fallback when the source is empty. Unowned metadata becomes
duplicated metadata across every generated page.
*Check:* generate metadata for a fixture set and assert uniqueness, presence and length per template.

**SEO-05 Structured data.** JSON-LD only — it is the format every major platform supports. The
load-bearing types as of mid-2026 are `Organization`, the correct content type (`Article`, `Product`,
`Event`, `Recipe`, `JobPosting`…), and `BreadcrumbList`; `Person` where authorship carries weight;
`FAQPage` **only where genuine question-and-answer content exists on the page**. Every value in the
markup must be present in the visible page.
*Check:* validate against a schema validator in CI; assert each marked-up field maps to rendered
content. Markup describing content a user cannot see is a manual-action risk and a Sev-1, not a
shortcut.

**SEO-06 Sitemaps and status codes.** XML sitemap generated from the same source of truth as the
routes, containing only indexable, canonical, 200-returning URLs. Missing pages return 404 or 410 —
not 200 with an empty shell, which is the default failure mode of client-side routers.
*Check:* assert a known-missing path returns 404; assert every sitemap entry returns 200 and is
self-canonical.

**SEO-07 Internal linking.** Every indexable page reachable from at least one other indexable page by
a crawlable `<a href>`. Not a click handler, not a button, not a router call. Pagination exposes real
links.
*Check:* crawl from the root with a link-following crawler and assert every sitemap URL is reachable.

**SEO-08 Core Web Vitals, as numbers at p75 of real users.** As of July 2026 the "good" thresholds are
**LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1** — verify these before making them blocking, as the metric set
has been revised before. Set a lab budget too, since field data does not exist before launch.
*Check:* Lighthouse or equivalent in CI against the budget, plus a named field-data source
post-launch.

**SEO-09 Internationalisation.** Only where more than one language or region ships. Reciprocal
`hreflang`, one canonical per locale, an `x-default`, and no automatic redirect that traps a user in
the wrong locale.
*Check:* assert reciprocity across the locale set; assert a manual locale choice persists.

**SEO-10 Media and assets.** Descriptive `alt` on content images, explicit dimensions to avoid layout
shift, modern formats, lazy loading below the fold and never on the LCP element.
*Check:* assert `alt` presence on content images and that the LCP element is not lazy-loaded.

**Advisory, and honest about it.** Keyword research, content calendars, link acquisition and topical
authority work all matter and none of them changes a build decision. They belong in the ledger or the
content contract, not in a blocking engineering gate.

---

# Part B — AI readiness (LLM Specialist)

## B0. What is actually known — read this first

Three facts that determine whether this contract is useful or cargo-cult. All verified July 2026;
re-verify before relying on them.

- **`llms.txt` is a community convention, not a standard, and largely not consumed.** Adoption sits
  around 8–10% of large sites. No major model provider has publicly committed to reading it in
  production; Google has stated it does not support it and has no plans to. Some Microsoft and OpenAI
  crawlers have been observed fetching it. It costs almost nothing to publish and it is not a
  strategy — mark it **advisory** and say why.
- **No file or markup buys citation.** There is no machine-readable artefact that earns AI visibility.
  Google has been explicit about this.
- **What does move citation is substantive.** Published research on generative-engine optimisation
  finds the largest gains from *adding quotations* (~+28%) and *adding statistics* (~+26%), with
  citing sources close behind, and correct structured data associated with materially higher citation
  rates. In other words: verifiable, attributable, well-structured content. There is no shortcut
  hiding behind the acronym.

Write the contract accordingly. A short, dated, checked contract beats a comprehensive one written
from memory.

## B1. Access terms — a decision, not a default

**AI-01 Per-crawler access, decided deliberately and recorded.** `GPTBot`, `OAI-SearchBot`,
`ClaudeBot`, `PerplexityBot`, `Google-Extended`, `CCBot`, `Bytespider` and their peers are separately
addressable, and **training access, retrieval access and live-answer fetching are different grants.**
There is no setting that is right for everyone: a media business protecting licensable archive and a
documentation site that wants to be quoted should choose oppositely.

Put the choice to the human, record the decision and its reason in the ledger, and make `robots.txt`
match it. A product that blocks the crawlers whose citations it wanted — or opens training access
nobody agreed to — has an architecture problem that looks like a config line.
*Check:* assert the `robots.txt` user-agent blocks match the recorded decision, per bot.

**AI-02 `llms.txt` — advisory.** Publish if you like: a short index of the canonical documentation
URLs with one line each. Do not claim it as the mechanism. Never let it drift from the real site, and
never let it contain content that is not also reachable in HTML.
*Check:* if published, assert every URL in it returns 200 and is canonical.

## B2. Retrievability — does a fragment survive extraction

Content reaches a model as fragments, not pages. These rules keep a fragment true.

**AI-03 Content in the server response.** Same requirement as SEO-01 and the same check. A crawler
that does not execute JavaScript sees nothing else, and most do not.

**AI-04 Self-contained passages.** Each section intelligible quoted alone: the answer near the
question, entities named in full at least once per section rather than "it" or "the platform", no
"as mentioned above", no pronoun whose referent is two paragraphs back.
*Check:* extract three sections at random and read them in isolation. If any is unintelligible or
misleading alone, it fails.

**AI-05 Facts carry figures, dates and sources.** The claim, the number, when it was true, and where it
came from. This is the highest-leverage rule in Part B and it is indistinguishable from good writing.
*Check:* sample the shipped content and assert each factual claim has an attached figure or source.

**AI-06 Honest freshness.** A visible date that reflects real change to the content. Never bumped to
look current. A `dateModified` in structured data must match the visible date and both must match
reality.
*Check:* assert `dateModified` equals the visible date and changes only when content changes.

**AI-07 Structured data as the entity layer.** Reuse SEO-05. `Organization` with consistent
`sameAs` identity across surfaces is what lets a model resolve you to one entity instead of three.

## B3. Agent-usability — can software do the job

This is where most "AI-ready" work stops short and where the value actually is.

**AI-08 If a human can complete it, state what an agent needs to.** A documented, stable, versioned,
authenticated interface for the primary jobs. Machine-readable identifiers for the objects a human
sees in the UI.
*Check:* complete one primary job end-to-end through the documented interface alone, and paste the
transcript.

**AI-09 Honest status codes and errors.** Semantic HTTP status codes. Errors that name what was wrong
and what to do — never 200 with an error page, which is the failure that makes a product silently
unusable by software.
*Check:* assert status codes and error shapes per interface contract.

**AI-10 Discoverable limits.** Pagination, rate limits and quotas documented and signalled in
response headers, not learned by being blocked.
*Check:* assert rate-limit headers present and the documented limit triggers the documented status.

**AI-11 Machine-readable interface description.** OpenAPI, a published schema, or an MCP server
descriptor — whichever fits. The interface contract itself is the Architect's `interfaces.md`; this is
a requirement *on* it, not a second copy of it.
*Check:* the description validates and matches the live interface for a sampled subset.

## B4. If the product itself embeds a model

That is a security surface before it is a feature. Retrieved content is untrusted input; model output
reaching a sink is untrusted at that sink; tools run least-privilege; loops carry iteration and cost
ceilings. **Those rules live in `security.md` with the Security Architect** — cross-reference them
here, do not copy them. Two versions of a security rule drift, and the weaker one gets followed.

## B5. What is refused

Off the table, and each a Sev-1 rather than a growth tactic:

- Serving different content to crawlers than to users
- Markup describing text a user cannot see
- Pages generated only to be retrieved, with no reader in mind
- Dates that misrepresent when content changed
- Fabricated statistics, quotations or sources — including plausible-looking ones. This rule exists
  because the highest-leverage technique in B2 is "add statistics and quotations", and the cheapest
  way to satisfy it is to invent them. Every figure traces to a real source or it does not ship.

---

## Writing either contract

One row per selected rule:

| ID | Rule | Applies to | Check | Blocking |
|----|------|-----------|-------|----------|
| SEO-01 | Primary content in initial HTML | All `/blog/*`, `/docs/*` | `curl` + assert selector present | Yes |

Then two short sections:

**Notes** — three to five sentences on what discoverability actually means for *this* product. A
documentation site, an internal tool behind auth, and a consumer marketplace need almost disjoint
subsets of this file, and the generic rules only catch generic problems.

**Accepted gaps** — what you are knowingly not doing this cycle and why, with a name attached. Written
down, it is a decision rather than an oversight, and it stops the same gap being rediscovered as a
Phase 3 finding by someone who had no idea it was deliberate.
