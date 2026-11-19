# 15-minute pitch

Use the headings below as the six screens for the presentation. The proposal contains the budget table, updated journeys and system diagram.

| Time | Screen | Talking points |
| --- | --- | --- |
| 0:00–2:00 | Decision | Protect continuity in one CRM market. Preserve the original delivery objective with a one-DC shadow pilot. Ask for conditional approval. |
| 2:00–4:30 | Budget | Show the move from 100 to 70 units, the spending ceilings and contingency. Explain how discovery tests real cost, staffing and deadline assumptions. |
| 4:30–7:00 | What changes for people | Walk through a missing pick confirmation and an active case that follows its owner into Salesforce. Explain the manual handoff and what stays in the archive. |
| 7:00–10:00 | Architecture and cutover | Show the two independent paths. Explain repeatable loads, delta reconciliation, sign-off, and what happens if the source is shut down. |
| 10:00–13:00 | Sequence and trade-offs | Show the eight-week planning scenario and the gate before onboarding the DC. Explain the cost of deferring multi-site rollout, automation and full history import. |
| 13:00–15:00 | Decision and proof | Ask for named owners, discovery authorization and a cutover window. Show which measures inform a later live trial and when to defer the pilot. |

## Judge Q&A

- **Can you deliver both for 70?** The split is a planning ceiling. Discovery validates committed spend, target licenses, vendor overlap, data complexity and available staff. If CRM consumes the headroom, defer the pilot's operational onboarding.
- **What if a record already exists in Salesforce?** Map stable source IDs and verify business-owned matching rules before the baseline load. Quarantine ambiguity so a retry cannot silently merge two customers.
- **What if the CRM switch fails?** Stop before releasing target writes when reconciliation fails. Reopen the source only during confirmed overlap. Otherwise run the rehearsed continuity queue, recover forward and account for every queued item.
- **Why avoid a CRM integration for the pilot?** The warning depends on order promises and fulfilment events. Manual service handoff keeps those inputs available throughout CRM cutover and lets us measure handoff demand before automating it.
- **How do you prove value?** Report actionable alerts and response against the agreed thresholds. Compare delivery outcomes against the original promise and baseline. A shadow pilot shows whether operators can use the alerts. A live trial is needed to estimate impact on deliveries.
