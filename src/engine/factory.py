"""Build a named policy instance from configs/engine.yaml + calibrated thresholds.json.
Policy names: 'ai', 'static_rule', 'hybrid', or 'fixed_T<N>' for each N in policies.fixed_interval.T_values."""
from __future__ import annotations

import re

from src.engine.policies import AIPolicy, FixedIntervalPolicy, HybridPolicy, StaticRulePolicy

_FIXED_RE = re.compile(r"^fixed_T(\d+)$")


def policy_names(ecfg: dict) -> list[str]:
    return ["ai", "static_rule", "hybrid"] + [f"fixed_T{T}" for T in ecfg["policies"]["fixed_interval"]["T_values"]]


def build_policy(name: str, ecfg: dict, levels: dict):
    p = ecfg["policies"]
    if name == "ai":
        return AIPolicy(levels, **p["ai"])
    if name == "static_rule":
        return StaticRulePolicy(levels, **p["static_rule"])
    if name == "hybrid":
        return HybridPolicy(AIPolicy(levels, **p["ai"]), **p["hybrid"])
    m = _FIXED_RE.match(name)
    if m:
        return FixedIntervalPolicy(T=int(m.group(1)))
    raise ValueError(f"unknown policy name: {name}")


def fsm_cooldown_for(name: str, ecfg: dict) -> int:
    """The mitigation FSM's own post-rotation dwell. For 'ai'/'hybrid' this matches the policy's own
    cooldown (consistent behaviour). The conventional baselines ('static_rule', 'fixed_T*') get a minimal
    dwell (1 window) deliberately, so their lack of built-in discipline still shows up as extra rotations
    in the cost metrics — that contrast is part of the E3 story, not an oversight."""
    if name in ("ai", "hybrid"):
        return int(ecfg["policies"]["ai"]["cooldown_windows"])
    return 1
