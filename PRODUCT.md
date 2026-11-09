# Product

## Platform

web

## Users

Primary: the DC coordinator at a Swedish distribution centre, working a full shift at a desk in the DC office (laptop or external monitor, office light), handling exceptions while phoning the warehouse floor.
Secondary: the shift lead, who takes escalations and is the only role allowed to approve an expedite.
Other stakeholders named in the Round 1 proposal (store staff, customer service, COO) are not users of this MVP's screens.
Secondary: the integration desk, which receives a data-quality task when a feed goes quiet.
The desk-office scene comes from the Round 1 proposal.

## Product Purpose

PromiseOps detects orders that may miss their original delivery promise, tells the coordinator how long is left to intervene and who owns each case, records what was done, and measures the outcome against the original promise.
Success for this MVP: a functional tool that demonstrates the closed loop (detect, own, act, prove) on one realistic morning, with honest measurement a pilot could reuse.

## Positioning

A closed loop around the original delivery promise: intervention deadline, one accountable owner, an allowed action, and a verifiable outcome.
It is not a dashboard of alerts and not a replacement for ERP, WMS or routing.

## Operating Context

Reads existing order and fulfilment systems; never writes back.
Rules-based and explainable; no AI in the core flow.
A demo harness (simulated clock, scripted feeds, feed-outage switch) stands in for real systems and wall-clock time in the video.

## Capabilities and Constraints

Two exception types: pick not confirmed, dispatch not confirmed.
Priority by time left to the intervention deadline, ties to B2B.
15-minute response timer with automatic escalation to the shift lead.
Outcomes: verified false alarm, expedited (shift lead only, with a logged cost), handed to customer service, auto-cleared; every human outcome needs written evidence.
The original promise is immutable.
Alerts pause when the fulfilment feed is older than 30 minutes or was not read after the milestone; such controls are shown as unknown.
An order past its promise without a delivery counts as late at once.
Outcomes show the Round 1 pilot scorecard and value only as an assumption (EUR 25 per prevented late delivery).
Pages: exception queue, exception detail, orders, outcomes (KPI), data health.
UI copy in English and Vietnamese; all data is fictional.

## Brand Commitments

Name: PromiseOps. Team: NgaChainAILayer2.
User priority for the visual work: "looks like a real product" over novelty.
No Netcompany branding (organiser of the challenge).

## Evidence on Hand

Round 1 proposal and business case (NgaChainAILayer2 deck, 10 slides).
No real Company A data, customers, testimonials or benchmarks exist; none may be invented.

## Product Principles

- Show time left and ownership before anything else.
- Never make silence look like success: stale data is shown, not hidden.
- Human decides, system records; every outcome is attributable.
- Measure against the promise made, never a moved target.
