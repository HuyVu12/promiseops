"""Market configuration. Shared engine, local rules: each market tunes thresholds and roles here."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketConfig:
    code: str
    name: str
    tz: str
    ack_sla_min: int  # minutes an owner has to acknowledge before escalation
    stale_after_min: int  # source older than this stops absence-based alerts
    poll_interval_min: int  # how often the adapter reads source feeds
    coordinator: str
    shift_lead: str
    data_owner: str


MARKETS: dict[str, MarketConfig] = {
    "SE": MarketConfig(
        code="SE",
        name="Sweden",
        tz="Europe/Stockholm",
        ack_sla_min=15,
        stale_after_min=30,
        poll_interval_min=5,
        coordinator="Anna Lind",
        shift_lead="Erik Berg",
        data_owner="Integration desk",
    ),
}

ROLES = {
    "coordinator": "DC coordinator",
    "shift_lead": "Shift lead",
}

EVENT_TYPES = ("PICK_CONFIRMED", "DISPATCHED", "DELIVERED")

EXCEPTION_TYPES = {
    "MISSING_PICK": "Pick not confirmed",
    "MISSING_DISPATCH": "Dispatch not confirmed",
}

RESOLUTIONS = {
    "FALSE_ALARM": "Verified on floor - alert was wrong",
    "EXPEDITED": "Expedited by shift lead",
    "CUSTOMER_NOTIFIED": "Promise at risk - handed to customer service",
    "AUTO_CLEARED": "Missing event arrived before anyone acted",
}

# Who may record which outcome. Expediting spends warehouse capacity, so only the shift lead decides.
RESOLUTION_ROLES = {
    "FALSE_ALARM": {"coordinator", "shift_lead"},
    "EXPEDITED": {"shift_lead"},
    "CUSTOMER_NOTIFIED": {"coordinator", "shift_lead"},
}

FULFILMENT_SOURCE = "wms"
ORDER_SOURCE = "oms"
