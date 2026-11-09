# MVP.mp4 - recording script (target 6:00, hard limit 7:00)

Record the browser at 1440x900 (or 1920x1080 at 125% zoom), English UI.
Before recording: run `.un.ps1` in the repository root, open http://127.0.0.1:8000/app?lang=en, click **Reset scenario**, sign in as **DC coordinator**.
Recorder: OBS Studio or Xbox Game Bar (Win+G).
Narration is in English; `MVP.srt` in this folder has the same lines as subtitles if you prefer on-screen text.
Do not show API keys, passwords or other windows.

| # | Time | On screen (do exactly this) | Narration |
|---|---|---|---|
| 1 | 0:00-0:30 | Landing page `/`, scroll once slowly, then click **Open the live demo** | Hi, we are team NgaChainAILayer2. In Round 1 we proposed PromiseOps for Company A: catch orders that are about to miss their original delivery promise early enough to save them. This is the working MVP. It runs locally, all data is fictional, and a demo harness at the bottom of the screen stands in for the real order and warehouse systems and the clock. |
| 2 | 0:30-1:00 | Queue at 09:00, empty. Point at the left rail feeds and the hour axis | It is 09:00 at DC Stockholm South. Every order is drawn as a course of four controls on one timetable: pick, dispatch cutoff, last viable dispatch, and the promise. The red line is now. Both data feeds are fresh. Nothing needs attention yet. |
| 3 | 1:00-1:35 | Click **+30 min**. Hover SE-1042 row | At 09:30 two orders appear. SE-1042 has no pick confirmation, and its route leaves at 10:00, so we have thirty minutes to act. The rule only fires because the warehouse feed was actually read after 09:30; silence is never treated as proof. Each exception gets one owner, Anna, and a fifteen-minute response timer. |
| 4 | 1:35-2:05 | Open **SE-1051**, **Take ownership**, choose *Verified on floor - alert was wrong*, type "Picker confirms tote packed 09:20, handheld offline", **Record outcome** | Anna checks SE-1051 first. The picker confirms it was packed at 09:20; the handheld synced late. She records it as a false alarm with evidence, which later tells us how precise our rules are. |
| 5 | 2:05-2:45 | Back to queue, open **SE-1042**, **Take ownership**. Show *Expedited* is disabled. Type escalation note "Not picked, picker on break. Need a priority pick for the 10:00 route", **Escalate** | SE-1042 is real: the goods were not picked. Expediting spends warehouse capacity, so a coordinator cannot approve it. Anna escalates to the shift lead with the reason. Decision rights are explicit in the product. |
| 6 | 2:45-3:15 | Rail: switch role to **Shift lead**. Choose *Expedited by shift lead*, note "Moved a picker from aisle 3, priority pick", **Record outcome**. Scroll to the activity log | Erik, the shift lead, reads the note, moves a picker and records the expedite, again with evidence. The activity log shows who did what and why. PromiseOps never writes back to the warehouse system; people act, the system records. |
| 7 | 3:15-3:50 | Switch back to coordinator. Click **Simulate feed outage**, then **+30 min**, **+15 min** | What if the warehouse feed goes quiet? After thirty minutes the feed turns red, a data task opens for the integration desk, and no new alerts are created, because an empty feed proves nothing. Orders picked during the outage do not become false alarms. |
| 8 | 3:50-4:10 | Click **Resume fulfilment feed**, **+5 min** | When the feed recovers, the backlog arrives first and only then do the rules run, on fresh data. |
| 9 | 4:10-4:45 | Go to **Orders**, click **+5 h**. Point at SE-1042 and SE-1077 | Fast forward to the afternoon. SE-1042 was picked and dispatched late, shown in brown, but delivered at 12:30, before its 14:00 promise. SE-1077 had no vehicle and nobody acted, so it arrives late and is counted late. Without the expedite, SE-1042 would also have been late. |
| 10 | 4:45-5:15 | Go to **Outcomes**. Point at the tiles and the margin strip | Outcomes are measured against the original promise, which can never be edited, with B2B and B2C reported separately: on-time rate, flagged orders still on time, time to ownership and false alarms. In the pilot these are compared against control stores before any business case is claimed. |
| 11 | 5:15-5:30 | Rail: switch **Language** to Tiếng Việt, show the queue, switch back | The interface also runs in Vietnamese; system messages are translated too. |
| 12 | 5:30-6:10 | Stay on Outcomes or show the README | What changed since Round 1. The scope is the one we proposed: one DC, two rules, owner, escalation, outcome log and measurement. We refined three things while building. First, the stale-data rule: a fixed 30-minute threshold still created false alarms, so a missing event now only counts if the feed was read after the milestone. Second, we added a demo harness so the whole morning can be shown in minutes. Third, the timetable view, because time left and ownership matter more than a list of alerts. As proposed, there is no AI inside the product. |
| 13 | 6:10-6:25 | Data health page, then back to queue | Under the hood: one FastAPI service, SQLite, idempotent ingestion, and 22 automated tests including a browser test of this journey. Thank you. |

## Checklist after recording

- Length under 7:00; export as MP4, file name `MVP.mp4`.
- Narration audible, or subtitles from `MVP.srt` burned in or attached.
- No other windows, notifications, passwords or keys visible.
