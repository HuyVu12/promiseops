# 15-minute pitch

Eleven slides, about 80 seconds each, then 10 minutes of questions. The slides are built by `scripts/build_round3_deck.py` into `docs/continuity/Round 3 Pitch.pdf`; the numbers come from the [proposal](README.md). Split the talk across three speakers so every member is seen; the fourth member runs the live demo on slide 8.

| Time | Slide | Speaker | Talking points |
| --- | --- | --- | --- |
| 0:00-1:00 | 1. Title | 1 | We passed Round 2 with a working MVP. Company A then cut the budget by 30% and made a CRM migration mandatory. Here is what we recommend now. |
| 1:00-2:30 | 2. Recommendation | 1 | Three decisions: Danish CRM to Salesforce first; PromiseOps keeps a one-DC shadow pilot on the MVP we already built; the same 12 weeks and two gates. EUR 126k. |
| 2:30-3:45 | 3. What changed and what we assume | 1 | The two client requests. Our assumptions, each checked at Gate 1: EUR 180k baseline, Denmark, existing Salesforce org, Dynamics readable until week 10. |
| 3:45-5:15 | 4. Budget | 2 | From EUR 180k to EUR 126k. CRM gets the largest share because it is mandatory. PromiseOps fits in EUR 27k because Round 2 already built the application: 88 person-days become 46. |
| 5:15-6:30 | 5. Keep, change, defer | 2 | What Round 1 promised and what happens to each item. The live pilot and the EUR 120k cohort are postponed, not cancelled. Unspent contingency brings the live phase back in weeks 13-16. |
| 6:30-7:45 | 6. System diagram | 2 | Two independent paths. PromiseOps reads OMS and WMS only; the CRM migration goes Dynamics, staging, Salesforce and archive. No integration between them, so neither can break the other. |
| 7:45-9:00 | 7. User journeys | 3 | The Swedish coordinator in shadow mode and the Danish CRM operator through cutover. What each person does differently from Round 2. |
| 9:00-10:30 | 8. MVP, adjusted | 4 (demo) | Live: shadow banner, a shift lead decision recorded but not executed, a customer-service case reference, and Outcomes that refuse to claim prevented late deliveries in shadow mode. |
| 10:30-12:00 | 9. 12 weeks and the cutover | 3 | Gate 1 in week 2, shadow from week 7, CRM cutover in week 9, Gate 2 in week 12. Go/no-go rules, and recover-forward if Dynamics is already gone. |
| 12:00-13:45 | 10. Risks and the fallback ladder | 3 | What we give up first if money runs short: contingency, optional CRM scope, then PromiseOps drops to replay. CRM continuity is never cut. |
| 13:45-15:00 | 11. The ask | 1 | Approve EUR 126k with the two gates; name the Danish country lead, the DC owner and the migration owner; confirm the Dynamics switch-off date in writing. |

## Judge Q&A

- **Can you deliver both for EUR 126k?** The split is a planning ceiling. Gate 1 validates committed spend, target licences, vendor overlap, data complexity and available staff. If CRM consumes the headroom, the pilot drops to a historical replay on the existing MVP and CRM keeps its money.
- **Why not cut PromiseOps completely?** It costs EUR 27k because the application exists. Stopping it throws away the Round 2 investment and the labelled data the risk model needs, to save less than a quarter of the budget.
- **Why Denmark?** The brief does not say which country. Denmark keeps the CRM team apart from the Swedish pilot DC. If it is Sweden, the same integration staff are shared, so shadow onboarding moves after the cutover; the budget stays the same.
- **What does a shadow pilot prove?** That alerts are precise enough and people respond within 15 minutes, against the Round 1 thresholds. It cannot prove prevented late deliveries, and the MVP refuses to claim them in shadow mode. The 4-week live phase measures impact against control stores.
- **What if a record already exists in Salesforce?** Map stable source IDs and verify business-owned matching rules before the baseline load. Quarantine ambiguity so a retry cannot silently merge two customers.
- **What if the CRM switch fails?** Stop before releasing target writes when reconciliation fails. Reopen the source only during confirmed overlap. Otherwise run the rehearsed continuity queue, recover forward and account for every queued item.
- **Why no CRM integration for PromiseOps?** The warning depends on order promises and fulfilment events. A manual handoff with a case reference keeps those inputs independent of the cutover and lets us measure handoff demand before paying for an integration.
- **What happens to the EUR 354k/year business case?** It starts later. It moves to a new funding decision after the live phase shows real impact, which is the same evidence-first rule we proposed in Round 1.
- **Who pays the Salesforce licences?** We assume the Danish country pays steady-state licences from its operating budget, as it pays Dynamics today. The project pays only the overlap months. If that is wrong, it is a sponsor decision at Gate 1.
