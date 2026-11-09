# Surface brief: PromiseOps working app (/app, /exceptions, /orders, /kpi, /data)

Scope: the coordinator's working screens. Mode: Operate. Build path: code-led.
Audience and job: DC coordinator at a desk, full shift, triaging orders at risk of missing the original promise; shift lead approves expedites.
Constraints: keep every function, route behaviour and data-testid; English copy; fictional data; no AI in the product.
User direction (verbatim intent): layout and charts from Archipelago Timetable, inspiration from Orienteering Course, combine the strengths of both.

## Direction contract

THESIS: Every order is a course on one shared timetable. The screen refuses the category default of a flat table of alert pills; it shows where each order stands against time, so the gap between now and the next unpunched control is the thing you read first.

OWN-WORLD: Sea-blue timetable shell (#0f3b5f rail, #f5f6f3 paper ground, 1px hairlines, no shadows), tabular figures everywhere, and one overlay colour reserved for the promise: orienteering course purple #a626aa. Controls are circles on the course: punched (filled dot) confirmed, red ring missed, hollow ahead, double ring escalated. Amber and red appear only as state.

STORY: The coordinator sees which course is about to fail, opens it, takes ownership, records evidence, and later sees the outcome measured against the course that was never redrawn.

FIRST VIEWPORT: Left sea-blue rail (nav, live clock, role, feed health). Main: heading and lead line, then the timetable board: a header axis of hours with a 15-minute hairline grid, one NOW line crossing every row, open exceptions on top (time-left chip, order, issue, owner) each with its purple course, then the orders still on course in a quieter band. Primary action sits on the detail page beside the course.

FORM: Archipelago Timetable (assigned, position 5 of 7) fused with the Orienteering Course challenger's control vocabulary and purple course overlay. seed:3e3a242f947c5240

Signature interaction: the NOW line and every course redraw as the clock advances; hovering a row highlights its course and its stops' labels.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

The landing page (/) is a separate Persuade surface with its own brief.
