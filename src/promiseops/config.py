"""Market configuration and product vocabulary.

One shared engine, local rules: each market tunes thresholds and roles here (Round 1, slide 9).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketConfig:
    code: str
    name: str
    tz: str
    dc: str
    ack_sla_min: int  # minutes an owner has to take ownership before automatic escalation
    stale_after_min: int  # fulfilment feed older than this pauses absence-based alerts
    poll_interval_min: int  # how often the adapter reads source feeds
    pick_grace_min: int  # minutes after the pick milestone before "not confirmed" counts
    coordinator: str
    shift_lead: str
    data_owner: str


MARKETS: dict[str, MarketConfig] = {
    "SE": MarketConfig(
        code="SE",
        name="Sweden",
        tz="Europe/Stockholm",
        dc="DC Stockholm South",
        ack_sla_min=15,
        stale_after_min=30,
        poll_interval_min=5,
        # Round 1 proposed a 15-minute grace. The read-after-milestone rule already stops alerts from
        # a quiet feed, so the demo alerts at the milestone; the pilot tunes this from shadow-mode
        # false-alarm data (weeks 7-8).
        pick_grace_min=0,
        coordinator="Anna Lind",
        shift_lead="Erik Berg",
        data_owner="Integration desk",
    ),
}

DEFAULT_MARKET = "SE"

ROLES = {
    "coordinator": "DC coordinator",
    "shift_lead": "Shift lead",
}

EVENT_TYPES = ("PICK_CONFIRMED", "DISPATCHED", "DELIVERED")

EXCEPTION_TYPES = {
    "MISSING_PICK": "Pick not confirmed",
    "MISSING_DISPATCH": "Dispatch not confirmed",
    # Follow-ups: an alert closed as a false alarm must never silence the order. If the awaited event
    # is still missing at the next control, the case comes back.
    "PICK_STILL_MISSING": "Pick still missing after a false alarm",
    "DISPATCH_STILL_MISSING": "Dispatch still missing after a false alarm",
}

RESOLUTIONS = {
    "FALSE_ALARM": "Verified on floor - alert was wrong",
    "EXPEDITED": "Expedited by shift lead",
    "CUSTOMER_NOTIFIED": "Promise at risk - handed to customer service",
    "AUTO_CLEARED": "Missing event arrived before anyone acted",
}

RESOLUTION_SHORT = {
    "FALSE_ALARM": "False alarm",
    "EXPEDITED": "Expedited",
    "CUSTOMER_NOTIFIED": "Customer informed",
    "AUTO_CLEARED": "Cleared by data",
}

# Outcomes a person can record, in the order the form shows them.
HUMAN_RESOLUTIONS = ("FALSE_ALARM", "EXPEDITED", "CUSTOMER_NOTIFIED")

# Who may record which outcome. Expediting spends warehouse capacity, so only the shift lead decides.
RESOLUTION_ROLES = {
    "FALSE_ALARM": {"coordinator", "shift_lead"},
    "EXPEDITED": {"shift_lead"},
    "CUSTOMER_NOTIFIED": {"coordinator", "shift_lead"},
}

FULFILMENT_SOURCE = "wms"
ORDER_SOURCE = "oms"

# Round 1 business-case assumptions (slides 7 and 8). Shown as assumptions, never as measured results.
AVOIDED_COST_PER_LATE_EUR = 25  # average cash avoided per late delivery prevented, net of intervention
# Below this many cases a percentage is shown but not judged against its target.
MIN_SAMPLE_FOR_TARGET = 10
PILOT_TARGETS = {
    "coverage_pct": 95,  # usable order coverage
    "actionable_pct": 70,  # alerts verified actionable
    "ack_in_sla_pct": 90,  # acknowledged within the response time, staffed hours
}
