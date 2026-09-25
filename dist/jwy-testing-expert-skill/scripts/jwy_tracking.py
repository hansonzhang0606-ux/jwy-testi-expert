"""Pipelines-aware time tracking helpers for Jingweiyun.

The generic time-tracking skill cannot infer optional pipeline branches.
This adapter consumes the pipeline state and exposes only the tracking IDs
that were actually completed for the current requirement.
"""

from __future__ import annotations


PIPELINE_STEP_BY_TRACKING_ID = {
    "P1": "step1",
    "P2": "step2",
    "P3-1": "step3-1",
    "P3-2": "step3-2",
    "P3-3": "step3-3",
    "P4": "step4",
    "P5": "step5",
}


def missing_tracking_ids(state: dict, recorded_ids: set[str]) -> list[str]:
    """Return completed pipeline tracking IDs that still need a record."""
    eligible = state.get("tracking", {}).get("eligible", [])
    return [tracking_id for tracking_id in eligible if tracking_id not in recorded_ids]


def build_record(tracking_id: str, step_name: str, hours: float) -> dict:
    """Build the Jingweiyun-specific fields passed to the v6.2 recorder."""
    if tracking_id not in PIPELINE_STEP_BY_TRACKING_ID:
        raise ValueError(f"Unknown Jingweiyun tracking ID: {tracking_id}")
    return {
        "tracking_id": tracking_id,
        "pipeline_step": PIPELINE_STEP_BY_TRACKING_ID[tracking_id],
        "step": step_name,
        "time_saved_hours": hours,
    }
