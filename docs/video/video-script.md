# MVP.mp4 — recorded English script

Final video: 5:23. Recorded against commit `1e70c79`. All data is fictional. See `recording-notes.md` for media details and verification scope.

Actions run through TIA; the edit shows the action followed by its observed result during narration. The first scene uses the title card; the final three scenes use the changes, architecture and closing cards.

## 1. PromiseOps 1

We are team Nga Chain AI Layer Two. This is Promise Ops, our working MVP for protecting the original delivery promise. All data in this demonstration is fictional.

Actions:

- `{"do": "click", "target": "[data-testid=reset]"}`
- `{"do": "select", "field": "[data-testid=role]", "option": "coordinator"}`

## 2. PromiseOps 2

It is nine in the morning at Stockholm South. Each order follows four controls: pick, dispatch cutoff, last viable dispatch, and the promised delivery time. The red line marks now.

## 3. PromiseOps 3

The yellow controls simulate feeds and time. The rules, ownership checks and outcome calculations run inside the application.

## 4. PromiseOps 4

Let us move forward thirty minutes.

Actions:

- `{"do": "click", "target": "[data-testid=adv-30]"}`

## 5. PromiseOps 5

Two orders have missed their pick milestone. Order S E ten forty two comes first because business deliveries win ties. Its original promise is two in the afternoon.

Observed text required: `SE-1042`.

## 6. PromiseOps 6

The warehouse feed has been read after the milestone. That makes the missing confirmation actionable. We open the case.

Actions:

- `{"do": "click", "target": "[data-testid=row-SE-1042] a.order-link"}`

## 7. PromiseOps 7

Anna takes ownership. The system records her response and stops the fifteen minute escalation timer.

Actions:

- `{"do": "click", "target": "[data-testid=ack]"}`

## 8. PromiseOps 8

An expedite uses warehouse capacity. The coordinator cannot approve it, so Anna records the reason and escalates to the shift lead.

Actions:

- `{"do": "type", "field": "[data-testid=esc-note]", "value": "Pick not confirmed. Priority pick needed to protect the original delivery promise."}`
- `{"do": "click", "target": "[data-testid=escalate]"}`

Observed text required: `Pick not confirmed. Priority pick needed to protect the original delivery promise.`.

## 9. PromiseOps 9

We switch to the shift lead. This role has permission to record an expedite.

Actions:

- `{"do": "select", "field": "[data-testid=role]", "option": "shift_lead"}`

## 10. PromiseOps 10

Erik allocates a picker, records the evidence, and logs a ten euro intervention cost.

Actions:

- `{"do": "click", "target": "[data-testid=res-expedited]"}`
- `{"do": "type", "field": "[data-testid=resolve-note]", "value": "Priority pick assigned; warehouse confirms loading for the next available departure."}`
- `{"do": "type", "field": "[data-testid=resolve-cost]", "value": "10"}`

Observed text required: `Priority pick assigned; warehouse confirms loading for the next available departure.`.

## 11. PromiseOps 11

The outcome is recorded. The activity log preserves who owned, escalated and decided the case, with the evidence and cost.

Actions:

- `{"do": "click", "target": "[data-testid=resolve]"}`

## 12. PromiseOps 12

Next, we return to the coordinator and investigate order S E ten fifty one.

Actions:

- `{"do": "select", "field": "[data-testid=role]", "option": "coordinator"}`
- `{"do": "open", "url": "http://127.0.0.1:8768/app"}`
- `{"do": "click", "target": "[data-testid=row-SE-1051] a.order-link"}`
- `{"do": "click", "target": "[data-testid=ack]"}`

## 13. PromiseOps 13

The picker confirms that the goods were packed before the milestone. The handheld was offline. Anna closes this as a false alarm, with written evidence.

Actions:

- `{"do": "click", "target": "[data-testid=res-false_alarm]"}`
- `{"do": "type", "field": "[data-testid=resolve-note]", "value": "Picker confirms tote packed at 09:20; handheld was offline."}`
- `{"do": "click", "target": "[data-testid=resolve]"}`

Observed text required: `Picker confirms tote packed at 09:20; handheld was offline.`.

## 14. PromiseOps 14

What happens if the warehouse feed goes quiet? We pause it and advance forty five minutes.

Actions:

- `{"do": "open", "url": "http://127.0.0.1:8768/app"}`
- `{"do": "click", "target": "[data-testid=feed-pause]"}`
- `{"do": "click", "target": "[data-testid=adv-30]"}`
- `{"do": "click", "target": "[data-testid=adv-15]"}`

## 15. PromiseOps 15

The stale feed warning is visible. New absence based alerts pause, uncertain controls are marked unknown, and a data quality task opens.

## 16. PromiseOps 16

We resume the feed and advance five minutes. The backlog arrives before the rules evaluate the orders.

Actions:

- `{"do": "click", "target": "[data-testid=feed-resume]"}`
- `{"do": "click", "target": "[data-testid=adv-5]"}`

## 17. PromiseOps 17

Order S E ten seventy seven now has a genuine dispatch problem. It is picked, but no vehicle is available in time.

## 18. PromiseOps 18

Anna takes ownership and records a handoff to customer service, with the expected arrival time. This records the handoff; the MVP does not send a customer message.

Actions:

- `{"do": "click", "target": "[data-testid=row-SE-1077] a.order-link"}`
- `{"do": "click", "target": "[data-testid=ack]"}`
- `{"do": "click", "target": "[data-testid=res-customer_notified]"}`
- `{"do": "type", "field": "[data-testid=resolve-note]", "value": "No vehicle until 11:50. Customer service handoff recorded with expected arrival 14:35."}`
- `{"do": "click", "target": "[data-testid=resolve]"}`

Observed text required: `No vehicle until 11:50. Customer service handoff recorded with expected arrival 14:35.`.

## 19. PromiseOps 19

We move to Orders and advance five hours to see what actually happened.

Actions:

- `{"do": "open", "url": "http://127.0.0.1:8768/orders"}`
- `{"do": "click", "target": "[data-testid=adv-300]"}`

## 20. PromiseOps 20

Order ten forty two arrived at twelve thirty two, before its two o clock promise. Picking and dispatch were late, but the customer promise was protected.

## 21. PromiseOps 21

Order ten seventy seven arrived at fourteen thirty five. Informing the customer does not change the original promise: this delivery still counts as late.

## 22. PromiseOps 22

Outcomes closes the loop. We measure against the original promise, which cannot be edited.

Actions:

- `{"do": "open", "url": "http://127.0.0.1:8768/kpi"}`

## 23. PromiseOps 23

In this simulated morning, ninety three point three percent of orders are on time, and one late delivery was prevented. The ten euro action cost remains visible.

Observed text required: `93.3`.

## 24. PromiseOps 24

The twenty five euro value is a business case assumption, not a measured saving. Three alerts are also too few to judge the pilot targets. The scorecard makes that limitation visible.

## 25. PromiseOps 25

Now we replay the same morning without intervention. We reset and advance beyond the delivery promise.

Actions:

- `{"do": "click", "target": "[data-testid=reset]"}`
- `{"do": "click", "target": "[data-testid=adv-30]"}`
- `{"do": "click", "target": "[data-testid=adv-300]"}`
- `{"do": "click", "target": "[data-testid=adv-60]"}`

## 26. PromiseOps 26

Without action, order ten forty two arrives at fourteen twenty five. On time delivery falls to eighty six point seven percent. This is a controlled demo comparison, not a production result.

Actions:

- `{"do": "open", "url": "http://127.0.0.1:8768/kpi"}`

Observed text required: `86.7`.

## 27. PromiseOps 27

The interface also supports Vietnamese, including system messages.

Actions:

- `{"do": "select", "field": "[data-testid=lang]", "option": "vi"}`

## 28. PromiseOps 28

We return to English for the final overview.

Actions:

- `{"do": "select", "field": "[data-testid=lang]", "option": "en"}`

## 29. PromiseOps 29

Since Round One, the milestone rule has gained a read after milestone check. It leaves time to act while avoiding alerts based on an unread feed. The demo harness and role switch stand in for real feeds and company sign in.

## 30. PromiseOps 30

Under the hood, one Fast API service combines ingestion, rules, workflow and read models with a SQLite database. It reads source events and never writes back to warehouse or order systems.

## 31. PromiseOps 31

The pilot will test these rules and collect labelled outcomes for later modelling. Today, the MVP demonstrates ownership, decision rights, evidence and honest measurement against the promise originally made. Thank you.
