# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: the DC coordinator at a Swedish distribution centre, working a full shift at a desk in the DC office (laptop or external monitor, office light), handling exceptions while phoning the warehouse floor.
Secondary: the shift lead, who takes escalations and is the only role allowed to approve an expedite.
Other stakeholders named in the Round 1 proposal (store staff, customer service, COO) are not users of this MVP's screens.
Context choice delegated by the user: "choose what is best"; the desk-office scene was picked from the Round 1 proposal.

## Product Purpose

PromiseOps detects orders that may miss their original delivery promise, tells the coordinator how long is left to intervene and who owns each case, records what was done, and measures the outcome against the original promise.
Success for this MVP: the Round 2 judges (Netcompany IT Consultant Challenge 2026) see a functional tool that demonstrates the closed loop and believe a real company could use it.

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
Outcomes: verified false alarm, expedited (shift lead only), handed to customer service, auto-cleared; every human outcome needs written evidence.
The original promise is immutable.
Alerts pause when the fulfilment feed is older than 30 minutes or was not read after the milestone.
Pages: exception queue, exception detail, orders, outcomes (KPI), data health.
All UI copy is English; all data is fictional.

## Brand Commitments

Name: PromiseOps. Team: NgaChainAILayer2.
User priority for the visual work: "looks like a real product" over novelty.
No Netcompany branding (organiser of the challenge).

## Evidence on Hand

Round 1 proposal and business case in `../../results/`.
No real Company A data, customers, testimonials or benchmarks exist; none may be invented.

## Product Principles

- Show time left and ownership before anything else.
- Never make silence look like success: stale data is shown, not hidden.
- Human decides, system records; every outcome is attributable.
- Measure against the promise made, never a moved target.
