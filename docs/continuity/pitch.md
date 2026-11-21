# 15-minute pitch

Twelve slides in 15 minutes, then 10 minutes of questions. The slides are built by `scripts/build_round3_deck.py` into `docs/continuity/Round 3 Pitch.pdf`; the numbers come from the [proposal](README.md). Split the talk across three speakers so every member is seen; the fourth member runs the live demo on slide 9.

| Time | Slide | Speaker | Talking points |
| --- | --- | --- | --- |
| 0:00-0:40 | 1. Problem statement | 1 | Introduce the delivery problem and how the brief changed over three rounds. |
| 0:40-1:40 | 2. Title | 1 | Introduce PromiseOps using the three times on the slide, then explain what changed in Round 3. |
| 1:40-2:30 | 3. Recommendation | 1 | Three decisions: Danish CRM to Salesforce first; PromiseOps keeps a one-DC shadow pilot on the MVP we already built; the same 12 weeks and two gates. EUR 126k. |
| 2:30-3:45 | 4. What changed and what we assume | 1 | The two client requests. Our assumptions, each checked at Gate 1: EUR 180k baseline, Denmark, existing Salesforce org, Dynamics readable until week 10. |
| 3:45-5:15 | 5. Budget | 2 | From EUR 180k to EUR 126k. CRM gets the largest share because it is mandatory. PromiseOps fits in EUR 27k because Round 2 already built the application: 88 person-days become 46. |
| 5:15-6:30 | 6. Keep, change, defer | 2 | What Round 1 promised and what happens to each item. The live pilot and the EUR 120k cohort are postponed, not cancelled. Unspent contingency brings the live phase back in weeks 13-16. |
| 6:30-7:45 | 7. System diagram | 2 | Two independent paths. PromiseOps reads OMS and WMS only; the CRM migration goes Dynamics, staging, Salesforce and archive. No integration between them, so neither can break the other. |
| 7:45-9:00 | 8. User journeys | 3 | The Swedish coordinator in shadow mode and the Danish CRM operator through cutover. What each person does differently from Round 2. |
| 9:00-10:30 | 9. MVP, adjusted | 4 (demo) | Live: shadow banner, a shift lead decision recorded but not executed, a customer-service case reference, and Outcomes that refuse to claim prevented late deliveries in shadow mode. |
| 10:30-12:00 | 10. 12 weeks and the cutover | 3 | Gate 1 in week 2, shadow from week 7, CRM cutover in week 9, Gate 2 in week 12. Go/no-go rules, and recover-forward if Dynamics is already gone. |
| 12:00-13:45 | 11. Risks and the fallback ladder | 3 | What we give up first if money runs short: contingency, optional CRM scope, then PromiseOps drops to replay. CRM continuity is never cut. |
| 13:45-15:00 | 12. The ask | 1 | Approve EUR 126k with the two gates; name the Danish country lead, the DC owner and the migration owner; confirm the Dynamics switch-off date in writing. |

## Opening for slide 1

Hi everyone. Our project started with a question about late deliveries. How does a warehouse coordinator find out an order is in trouble while there's still time to do something?

In Round 1 we proposed a way for coordinators to catch those orders sooner. In Round 2 we built it and showed how a coordinator would use it. For Round 3, the budget is 30% smaller and the project also has to cover a CRM migration. Before we get into the revised plan, here's what our tool does on a normal morning.

## Opening for slide 2

Here's an example from our demo. An order is due at two, and the truck leaves at ten. It's half past nine, and the warehouse hasn't confirmed that the order has been picked. PromiseOps flags the order and shows the coordinator how much time they have. Someone takes ownership of the case, and later we can see whether the order arrived by two.

We'd move the country's CRM from Dynamics 365 to Salesforce first and use the tool we've already built to run a smaller trial at one distribution centre. During the trial, the warehouse team would still make dispatch decisions the way they do today.

## Live demo for slide 9 (90 seconds)

Start it before the session, on the presenting laptop, and leave the tab open on the queue:

```powershell
$env:PROMISEOPS_SHADOW = "1"; $env:PROMISEOPS_DB = "$env:TEMP\round3-demo.db"
python -m uvicorn --app-dir src promiseops.web.app:app --port 8767
```

Open http://127.0.0.1:8767/app?lang=en, choose **DC coordinator** in the rail, click **Reset scenario**, then **+30 min**.

1. Point at the blue banner: shadow pilot, the floor process still decides.
2. Open **SE-1042**, **Take ownership**, escalate with "Not picked, need a priority pick".
3. Switch the role to **Shift lead**, choose **Expedited by shift lead**, note "Would move a picker", cost **10**, **Record outcome**. Show the "Shadow mode" line in the activity log.
4. Switch back to **DC coordinator**, **+30 min**, open **SE-1077**, **Take ownership**, choose **handed to customer service**, note "No vehicle until 11:50", case reference **CS-48213**, **Record outcome**. Show "Handed over" in the log.
5. Open **Outcomes**: late deliveries prevented is 0, "Not claimed in shadow mode".

If the laptop or the network fails, stay on slide 9: its four screenshots are the same steps.

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
