# Verticals

Reference for the **Domain Analyst**. Each entry is a starting point for
`/loop-project/0-plan/domain.md`, not a substitute for it.

Read only your vertical's section. Reading all twenty is a token tax with no payoff, and the Analyst
who does it writes a worse brief than the one who read one section and then researched.

---

## How to use this

Each entry gives four things: the **table stakes** a newcomer forgets, the **regimes** that may
apply, the **vocabulary traps**, and the **integration reality**. None of them is a compliance
opinion and none is current by virtue of being written down.

**Three rules that matter more than the contents of this file:**

1. **Verify before you assert.** Every regime named here has changed at least once and several are
   mid-change right now. Search for current status, thresholds and dates, and record what you
   verified and when. An undated regulatory claim is one nobody can re-check.
2. **State the trigger, not just the regime.** "GDPR applies" is useless. "Processing health data of
   EU residents brings Article 9 into scope, which forces an explicit lawful basis and a DPIA" is a
   constraint someone can build against. A regime listed without its trigger is either ignored or
   over-applied.
3. **This is not legal advice and neither is your brief.** Where the consequence of being wrong is
   regulatory, flag it for a human with the relevant qualification. A flagged unknown costs a
   conversation. A confident error costs a rebuild, and sometimes more.

### Cross-cutting — check these in every vertical

| Area | Why it reaches nearly everything |
|---|---|
| **GDPR / UK GDPR / CCPA-CPRA** | Any personal data. Lawful basis, minimisation, subject rights, retention, cross-border transfer. |
| **Accessibility** | The European Accessibility Act has been enforceable since 28 June 2025 for consumer-facing digital products sold into the EU, including from outside it, with narrow micro-enterprise relief. WCAG 2.x AA is the operative technical bar — confirm which version the current harmonised standard names. |
| **EU AI Act** | Any AI feature. Prohibited-practice rules and GPAI obligations already bite; the high-risk timetable has been amended and is still moving — verify current dates before you rely on one. Hiring, credit, education, and essential-services decisioning are the usual high-risk triggers. |
| **Payments** | PCI DSS the moment card data is in scope. Using a hosted processor reduces scope; it does not remove it. |
| **Records and audit** | Most regulated verticals require an append-only, attributable, time-stamped trail. Retrofitting one is a data-model change, not a feature. |

---

## Fintech

**Table stakes.** Double-entry ledger with immutable postings. Reconciliation view someone can
actually work from. Idempotent payment initiation. Statement export in a format an accountant
accepts. Multi-currency handling decided before the first row is written, including rounding.

**Regimes.** KYC/AML with sanctions and PEP screening. Strong customer authentication and the
PSD2 / PSD3-and-PSR successor package — verify the current stage. PCI DSS where card data is in scope.
MiCA for crypto-asset activity in the EU. Consumer credit rules where lending is involved. Local
money-transmission or e-money licensing, which is jurisdiction-by-jurisdiction and often the real
blocker.

**Vocabulary traps.** *Settlement* vs *clearing* vs *authorisation*. *Balance* — available, ledger,
or pending. *Reversal* vs *refund* vs *chargeback*. Never store money as a float.

**Integration reality.** Open banking APIs with per-bank quirks. Card networks and acquirers. ISO
20022 migration. Nightly batch files that are still the authoritative source. Bank data arrives late,
duplicated, and occasionally restated.

---

## Healthtech

**Table stakes.** Per-record access control with a reason-for-access trail. Patient identity matching
that expects duplicates. Clinical audit log. Explicit handling of amended and superseded records —
clinical data is corrected, never silently overwritten. A safe fallback when data is missing, because
absence is clinically meaningful.

**Regimes.** HIPAA in the US; GDPR Article 9 special-category data in the EU/UK. Software as a medical
device brings EU MDR or FDA classification into scope — the trigger is intended purpose, and "clinical
decision support" crosses it more easily than teams expect. IEC 62304 for software lifecycle, ISO
13485 for quality management, ISO 14971 for risk. Local data-residency rules.

**Vocabulary traps.** *Encounter* vs *episode* vs *visit*. *Patient* vs *subject* vs *service user*.
*Observation* has a specific FHIR meaning. Units and reference ranges are not universal.

**Integration reality.** HL7 v2 still everywhere, FHIR increasingly, both at once in practice. DICOM
for imaging. SNOMED CT, LOINC, ICD coding systems. Hospital integration timelines are measured in
quarters and gate your launch more than your build does.

---

## Proptech

**Table stakes.** Property identity that survives being renamed, subdivided or renumbered. Tenancy
schedule with rent review and break dates. Document pack per property with version history.
Multi-party permissions — landlord, agent, tenant, contractor, buyer — that are genuinely separate.
Money-in / money-out per property with client-money separation where it applies.

**Regimes.** AML with source-of-funds checks on transactions. Client money protection and tenancy
deposit rules. Energy performance certificate display duties. Local tenancy law, which is intensely
jurisdictional and dictates notice periods and permitted fees. RICS or equivalent valuation standards
where you state a value. Land registry procedure for anything touching title.

**Vocabulary traps.** *Unit* vs *property* vs *asset* vs *lot*. *Yield* — gross, net, or reversionary.
*Void* vs *vacant*. *Completion* vs *exchange* vs *closing*, which differ by country.

**Integration reality.** Portal feeds and their schemas. Land registry and cadastral data. Referencing
and credit-check providers. Accounting packages. Address data is dirty and UPRN-style identifiers are
worth adopting early.

---

## Agritech

**Table stakes.** Field and parcel geometry with history, because boundaries change. Season and crop
cycle as first-class concepts. Traceability from input to harvested lot. Offline capture — connectivity
in a field is not a given, and sync conflict handling is a design decision, not a bug fix.
Machine-data ingestion that tolerates gaps.

**Regimes.** Subsidy and land-parcel reporting where it applies, CAP in the EU. Food safety and
traceability. Plant protection product usage records. Animal movement and welfare records for
livestock. Organic certification chain of custody.

**Vocabulary traps.** *Field* vs *parcel* vs *block* vs *paddock*. *Yield* per what area, at what
moisture. *Batch* vs *lot* vs *consignment*. *Application* means spraying here.

**Integration reality.** ISOBUS and machine telemetry, per-manufacturer. Satellite and drone imagery
with real latency. Weather providers. Sensor networks that go quiet. GIS formats that carry projection
mistakes.

---

## Regtech

**Table stakes.** Append-only, attributable, time-stamped evidence trail. Point-in-time reconstruction
— what did the record say on this date. Rule versioning with an effective date, because a rule changed
does not mean historic assessments were wrong. Maker-checker approval. Export in the regulator's own
format, which is usually the hardest part.

**Regimes.** Whatever your customer is regulated by — you inherit their obligations. Commonly SOX,
DORA for EU financial-entity operational resilience, NIS2, EMIR/MiFIR transaction reporting, Basel
reporting. Records retention with statutory minimum periods.

**Vocabulary traps.** *Control* vs *test* vs *evidence*. *Finding* vs *exception* vs *breach*.
*Effective date* vs *reporting date* vs *as-of date* — conflating these produces wrong reports that
validate cleanly.

**Integration reality.** Regulator submission portals with strict schemas and unhelpful errors. GRC
platforms. Customer data warehouses. Reporting deadlines are immovable and shape your architecture.

---

## Insurtech

**Table stakes.** Policy lifecycle with mid-term adjustment and endorsement history. Quote versioning
and audit of what was disclosed. Claims workflow with reserve tracking. Premium, tax and commission
split correctly at bind. Document generation that produces the exact wording sold.

**Regimes.** Solvency II or local capital regime for carriers. Insurance distribution rules covering
demands-and-needs and product oversight. Claims handling conduct rules. Pricing-practice rules
restricting differential renewal pricing in some markets. EU AI Act where models drive pricing or
claims decisions.

**Vocabulary traps.** *Premium* — gross, net, written, earned. *Loss* vs *claim* vs *incident*.
*Reserve* vs *provision*. *Binder* vs *policy* vs *certificate*.

**Integration reality.** Broker and MGA data exchange. Bordereaux spreadsheets, still. Reinsurance
reporting. Rating engines. Legacy policy admin systems with limited APIs.

---

## Legaltech

**Table stakes.** Matter-centric structure, not document-centric. Conflict-of-interest check before
engagement. Privilege and confidentiality boundaries enforced per matter, including ethical walls.
Immutable audit of who saw what. Retention and destruction schedules. Time recording that lawyers will
actually use.

**Regimes.** Legal professional privilege — a technical constraint, not a policy one. Client
confidentiality under the relevant bar rules. E-discovery preservation and legal hold. Client account
rules for money held. Unauthorised-practice-of-law limits on what AI output may assert.

**Vocabulary traps.** *Matter* vs *case* vs *engagement*. *Client* vs *party* vs *contact* — a party
may be an adverse one. *Filing* vs *service* vs *lodging*.

**Integration reality.** Court e-filing systems, per jurisdiction, often brittle. Document management
with strict versioning. Practice management and billing. Citation databases.

---

## Edtech

**Table stakes.** Learner progress that survives re-enrolment. Roster and hierarchy sync. Assessment
integrity controls. Guardian and teacher visibility as separate permission surfaces. Accessibility as
a hard requirement, not a phase two.

**Regimes.** FERPA and COPPA in the US, with COPPA's under-13 verifiable parental consent driving real
architecture. GDPR with children's-data provisions in the EU. Accessibility mandates — Section 508,
EAA, national equivalents. Safeguarding and reporting duties. EU AI Act treats some educational
decisioning as high-risk.

**Vocabulary traps.** *Course* vs *class* vs *section* vs *cohort*. *Grade* — a mark or a year group.
*Completion* vs *mastery* vs *attendance*.

**Integration reality.** LTI for tool interoperability, SCORM/xAPI for content, OneRoster for rosters.
SIS integrations that vary per district. Academic calendars that break assumptions annually.

---

## Climatetech

**Table stakes.** Emissions calculation with the factor set, version and source recorded per figure —
a number without its factor is unauditable. Scope 1, 2 and 3 kept structurally separate. Restatement
handling when factors update. Uncertainty carried rather than hidden. Evidence attached to every input.

**Regimes.** CSRD and ESRS reporting in the EU, with scope and timing amended more than once — verify
current status. GHG Protocol as the calculation standard. SBTi for target validation. ISO 14064.
Carbon-credit registry rules. Anti-greenwashing rules on the claims you let users publish.

**Vocabulary traps.** *Offset* vs *removal* vs *avoidance*. *Net zero* vs *carbon neutral* vs
*climate positive* — these have contested definitions and legal exposure. *Emission factor* vs
*activity data*. Units: tCO2e, not tC.

**Integration reality.** Utility and meter data with gaps. Supplier surveys that arrive incomplete.
Emission factor databases with licensing terms. ERP spend data used as a proxy, badly.

---

## Martech

**Table stakes.** Consent captured with its timestamp, scope, and the exact wording shown —
consent-as-a-boolean is the defect that causes the fine. Suppression and preference honoured across
every send path. Identity resolution with a merge that can be undone. Deliverability infrastructure —
SPF, DKIM, DMARC — before the first campaign.

**Regimes.** GDPR consent standard and the ePrivacy rules on cookies and tracking. CAN-SPAM and TCPA
in the US, the latter with real per-message damages. CCPA/CPRA opt-out including Global Privacy
Control. Platform-specific policy for each ad network.

**Vocabulary traps.** *Lead* vs *contact* vs *subscriber* vs *profile*. *Opt-in* — single or
double, and for which channel. *Attribution* — last-touch, first-touch, or modelled, which produce
different numbers from the same data.

**Integration reality.** CRM and CDP sync loops that double-count. Ad platform APIs with changing
schemas. Deprecating third-party cookies and server-side tagging. Event volumes that make naive
architectures expensive fast.

---

## HRtech

**Table stakes.** Effective-dated employment records — history is the product. Org hierarchy that
handles matrix reporting and mid-period change. Separation of recruiting data from employee data.
Sensitive-field access control. Payroll-grade correctness, where an off-by-one is somebody's rent.

**Regimes.** Employment law per jurisdiction, including working time and leave. GDPR, with
special-category data where health or diversity monitoring is involved. EU AI Act: employment
decisioning is a standard high-risk trigger. NYC Local Law 144 requires an independent bias audit for
automated employment decision tools. EEOC adverse-impact analysis in the US. Pay transparency
directives increasingly force stored comparator data.

**Vocabulary traps.** *Employee* vs *worker* vs *contractor* — legally distinct, differently taxed.
*Termination* vs *separation* vs *offboarding*. *FTE* vs *headcount*. *Salary* vs *total
compensation*.

**Integration reality.** Payroll providers per country. ATS and HRIS sync. SSO and directory
provisioning via SCIM. Benefits carriers on file feeds.

---

## Logistics and supply chain

**Table stakes.** Shipment identity stable across carrier handoffs. Event timeline with an
authoritative source per event. Dimensional and weight data with units declared. Exception handling as
a first-class flow, because exceptions are the job. Proof of delivery capture.

**Regimes.** Customs declarations with HS classification and origin. Incoterms determining who owes
what. Dangerous goods classification and documentation. Driver hours and electronic logging where
applicable. Sanctions screening on counterparties. Food and pharma cold-chain rules.

**Vocabulary traps.** *Shipment* vs *consignment* vs *order* vs *load*. *ETA* — promised, planned or
predicted. *Delivered* vs *completed* vs *closed*. Weight — gross, net, chargeable, volumetric.

**Integration reality.** EDI, usually EDIFACT or X12, still dominant. Carrier APIs of wildly varying
quality. Telematics feeds. Port and terminal systems. Timezones and daylight saving are a genuine
source of production defects here.

---

## Govtech

**Table stakes.** Case management with full decision audit and the reason recorded. Accessibility to
the mandated level, non-negotiable. Records retention and lawful disposal. Multi-language where
statutory. Service continuity assumptions that do not require the citizen to have a smartphone.

**Regimes.** Procurement rules shaping what you may even build. Accessibility mandates — Section 508,
EN 301 549, national equivalents. Freedom-of-information exposure of stored data. Records management
statutes. Security frameworks: FedRAMP, Cyber Essentials, national baselines. Algorithmic transparency
duties where decisions are automated.

**Vocabulary traps.** *Citizen* vs *resident* vs *applicant* vs *claimant*. *Application* vs *claim*
vs *request*. *Determination* vs *decision* vs *outcome* — appeal rights may attach to one and not
another.

**Integration reality.** Legacy mainframes and batch interfaces. National identity and verification
services. Payment services with prescribed flows. Long procurement and accreditation lead times.

---

## Defence and dual-use

**Table stakes.** Classification handling at the data layer, not the UI layer. Air-gapped or
restricted-network operation as a design assumption. Full attribution audit. Supply-chain provenance
for every dependency. Cryptographic requirements set by the customer, not by you.

**Regimes.** ITAR and EAR export control — this constrains who may see the code, not only the product,
and it is the constraint teams discover latest and most expensively. NIST SP 800-171 and CMMC for US
defence contractors. National security vetting for personnel. Data residency and sovereignty.

**Vocabulary traps.** *Classified* has specific levels with specific handling. *Release* means export
authorisation. *Requirement* may be a contractual deliverable with a compliance matrix behind it.

**Integration reality.** Restricted environments with no internet egress. Approved-software lists.
Standards-based interfaces, often STANAG or MIL-STD. Accreditation timelines that dominate the plan.

**Note.** Confirm scope and permissible activity with the human before doing any work here. This is a
vertical where a well-intentioned build decision can be a criminal matter.

---

## Commerce and retail

**Table stakes.** Inventory truth with oversell handling. Price and tax computed per destination, not
stored per product. Order state machine including partial fulfilment, cancellation and return. Idempotent
checkout. Address validation. Refund path that reconciles to the payment.

**Regimes.** PCI DSS for card handling. Consumer rights and distance-selling withdrawal periods. VAT
and sales-tax registration thresholds and marketplace deemed-supplier rules. Product safety and
labelling. Cookie consent before any tracking fires.

**Vocabulary traps.** *Order* vs *cart* vs *checkout* vs *transaction*. *SKU* vs *variant* vs
*product*. *Available* — on hand, on hand less allocated, or including inbound. *Price* — with or
without tax, which differs by market convention.

**Integration reality.** Payment service providers and 3-D Secure flows. Tax engines. Warehouse and
3PL systems. Marketplace feeds. Fraud screening. Peak-season load an order of magnitude above normal.

---

## Wealthtech

**Table stakes.** Position and transaction history reconciled to a custodian. Performance calculation
with a stated methodology. Suitability record captured at the point of advice. Fee calculation and
disclosure. Corporate action handling.

**Regimes.** MiFID II suitability, appropriateness, costs disclosure and best execution in the EU/UK;
Reg BI and fiduciary standards in the US. Custody rules. KYC/AML. Marketing and financial promotion
rules on anything shown to a prospect. Vulnerable-customer duties.

**Vocabulary traps.** *Return* — gross, net, time-weighted, money-weighted. *Position* vs *holding* vs
*lot*. *Advice* vs *guidance* — the line has regulatory consequence. *Risk* — volatility, capacity for
loss, or tolerance.

**Integration reality.** Custodian and broker feeds. Market data with licensing terms that restrict
display. Reference data on instruments. Corporate action feeds that arrive late.

---

## Cybersecurity

**Table stakes.** Multi-tenant isolation you can demonstrate. Detection with tuned, explainable
alerts. Immutable audit. Agent or sensor update path that cannot brick a fleet. Least-privilege by
default with break-glass access that is logged.

**Regimes.** NIS2 in the EU with incident reporting on short clocks. SOC 2 and ISO 27001 as customer
requirements. Coordinated vulnerability disclosure. Sector rules where you serve regulated customers.
Data residency for telemetry.

**Vocabulary traps.** *Alert* vs *event* vs *incident* vs *detection*. *Vulnerability* vs *finding*
vs *risk*. *Asset* — device, identity, workload, or all three.

**Integration reality.** SIEM and SOAR platforms. Cloud provider audit logs. Identity providers.
Threat intelligence feeds with differing formats. Telemetry volume dominating cost.

---

## Biotech and life sciences

**Table stakes.** Sample chain of custody. Instrument data captured with its run metadata. Protocol
versioning with the executed version recorded per experiment. Electronic signature with attributable
identity. Reproducibility — inputs, versions, parameters preserved.

**Regimes.** GxP — GLP, GCP, GMP — depending on activity. 21 CFR Part 11 for electronic records and
signatures, driving audit trail and signature requirements directly into the data model. EU Annex 11.
Computer system validation. Clinical trial regulation and informed consent where human subjects are
involved.

**Vocabulary traps.** *Sample* vs *specimen* vs *aliquot*. *Run* vs *experiment* vs *assay*.
*Validation* means CSV here, not input checking.

**Integration reality.** LIMS and ELN systems. Instrument outputs in proprietary formats. Reference
databases. Validation effort typically exceeding build effort — plan for it in the milestones.

---

## Traveltech

**Table stakes.** Availability and price that are correct at the moment of booking, with a stated
staleness policy. Booking reference stable across changes. Cancellation and change flows with fee
computation. Traveller identity and document handling. Timezone correctness throughout.

**Regimes.** Package travel rules creating organiser liability and insolvency-protection duties.
IATA/BSP settlement rules for air. Passenger rights and compensation regimes. Advance passenger
information requirements. Consumer price-display rules requiring all-in pricing.

**Vocabulary traps.** *Booking* vs *reservation* vs *ticket* vs *PNR*. *Passenger* vs *traveller* vs
*guest*. *Cancelled* — by whom, and refundable on what terms.

**Integration reality.** GDS and NDC for air, each with quirks. Hotel channel managers. Payment with
multi-currency settlement. Rate and availability caching that goes stale under load.

---

## Foodtech

**Table stakes.** Allergen data as a structured, required field — never free text. Batch and lot
traceability both directions. Temperature and shelf-life tracking. Recipe versioning with a nutrition
recalculation. Supplier record with certification expiry.

**Regimes.** HACCP plans. Allergen labelling with mandatory declared allergens, and prepacked-for-direct-sale
rules in some markets. Nutrition declaration format. FSMA traceability in the US. Novel food
authorisation. Health and origin claim restrictions.

**Vocabulary traps.** *Batch* vs *lot* vs *production run*. *Best before* vs *use by* — one is safety,
one is quality, and confusing them in code is a public-health defect. *Ingredient* vs *component* vs
*additive*.

**Integration reality.** Supplier specification exchange. Nutrition databases. EPOS and delivery
platforms. Cold-chain sensors.

---

## Nothing above fits

Write the four sections anyway, from research rather than from a template. The structure is the
transferable part; the contents were never the point. Say in `domain.md` that no reference section
existed and what you used instead, so the next loop in this vertical starts from your work rather
than from a blank page.
