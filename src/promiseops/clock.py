"""Which clock the product runs on.

- demo (default): the simulated DC clock that the demo harness moves; feeds are scripted.
- pilot (PROMISEOPS_MODE=pilot): wall-clock time; real systems push records and heartbeats to the JSON
  API, and a scheduler runs the rules every minute so response timers and the stale-feed guard fire on
  their own. The demo controls are switched off.

The engine and the workflow take ``now`` as an argument, so they are identical in both modes.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from promiseops.integration import simulation

DEMO = os.environ.get("PROMISEOPS_MODE", "demo").strip().lower() != "pilot"

# How often the scheduler runs the rules in pilot mode.
RULES_EVERY_SECONDS = 60


def mode() -> str:
    return "demo" if DEMO else "pilot"


def now(conn: sqlite3.Connection) -> datetime:
    if DEMO:
        return simulation.now(conn)
    return datetime.now(timezone.utc).replace(microsecond=0)
