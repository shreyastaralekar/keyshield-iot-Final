"""Trigger policies (implement TriggerPolicy from src/contracts.py: decide(state, score, t) -> Action).

`state` is a plain dict the CALLER creates per device via `init_state()` and passes back on every call;
each policy reads/mutates only the keys it owns. This lets the same device be run under different policies
independently (needed for the fixed-interval / static-rule / hybrid baselines in Experiment E3).
"""
from __future__ import annotations

from src.contracts import Action


class AIPolicy:
    """Adaptive, hysteresis-gated, cooldown-limited policy driven by a Batch 2 anomaly score.

    - A fast path lets a very severe score (>= rotate_level * fast_path_multiplier) trigger ROTATE
      immediately, bypassing hysteresis (so a sudden, severe attack is not missed while waiting).
    - Otherwise WARN/ROTATE require at least `hysteresis_k` of the last `hysteresis_n` windows to cross
      the level, so a single noisy window cannot trigger an action.
    - A cooldown blocks a second ROTATE too soon after the last one (this prevents a "rotation storm").
    - REVOKE fires only on PERSISTENCE: `revoke_persist_windows` consecutive windows at/above rotate_level
      while still within the post-rotation cooldown (i.e. the device stayed compromised despite rotating).
      REVOKE itself is never blocked by the rotation cooldown.
    - The per-device EWMA baseline is updated only on windows scored below rotate_level ("gated"), so a
      sustained attack cannot drag the device's own baseline upward and mask itself.
    """

    name = "ai"

    def __init__(self, levels: dict, hysteresis_n: int = 3, hysteresis_k: int = 2,
                fast_path_multiplier: float = 1.5, cooldown_windows: int = 10,
                revoke_persist_windows: int = 5, ewma_alpha: float = 0.05, warn_z: float = 2.5):
        self.levels, self.hn, self.hk = levels, hysteresis_n, hysteresis_k
        self.fast_mult, self.cooldown = fast_path_multiplier, cooldown_windows
        self.revoke_persist, self.alpha, self.warn_z = revoke_persist_windows, ewma_alpha, warn_z

    def init_state(self) -> dict:
        return {"warn_hist": [], "ewma_mean": self.levels["warn"], "ewma_var": 1e-6,
                "last_rotate_t": -10**9, "rotate_streak": 0, "in_cooldown_until": -1}

    def decide(self, state: dict, score: float, t: int) -> Action:
        lv = self.levels
        in_cooldown = t < state["in_cooldown_until"]

        # Fast path: unmistakably severe -> rotate immediately, no waiting for hysteresis. BUT this must
        # still respect cooldown: without the `not in_cooldown` guard, a sustained severe score (e.g. a
        # long flood attack sitting above rotate_level * fast_path_multiplier) would re-trigger this branch
        # on every single window forever, since t - last_rotate_t keeps growing — rotating every window
        # and never letting the persistence counter below reach revoke_persist_windows. That bug meant a
        # sustained severe attack could rotate indefinitely but never escalate to REVOKE.
        if score >= lv["rotate"] * self.fast_mult and not in_cooldown:
            state["last_rotate_t"], state["in_cooldown_until"] = t, t + self.cooldown
            state["rotate_streak"] = 1
            return "ROTATE"

        above_warn = score >= lv["warn"]
        z = (score - state["ewma_mean"]) / (state["ewma_var"] ** 0.5 + 1e-9)
        hist = state["warn_hist"]
        hist.append(bool(above_warn or z >= self.warn_z))
        if len(hist) > self.hn:
            hist.pop(0)
        hyst_fire = sum(hist) >= self.hk

        above_rotate = score >= lv["rotate"]

        if in_cooldown:
            # persistence check: still hostile after we already rotated -> escalate to REVOKE
            state["rotate_streak"] = state["rotate_streak"] + 1 if above_rotate else 0
            if state["rotate_streak"] >= self.revoke_persist:
                return "REVOKE"
            action = "WARN" if hyst_fire else "NONE"
        elif hyst_fire and above_rotate:
            state["last_rotate_t"], state["in_cooldown_until"] = t, t + self.cooldown
            state["rotate_streak"] = 1
            action = "ROTATE"
        elif hyst_fire:
            action = "WARN"
        else:
            action = "NONE"

        if score < lv["rotate"]:   # gated EWMA update: only learn from below-rotate ("benign-like") windows
            d = score - state["ewma_mean"]
            state["ewma_mean"] += self.alpha * d
            state["ewma_var"] = (1 - self.alpha) * (state["ewma_var"] + self.alpha * d * d)
        return action


class FixedIntervalPolicy:
    """Conventional baseline: rotate every T windows, regardless of any anomaly score. Never revokes
    (there is no concept of 'severity' in this baseline) — this is deliberate: it shows what a device
    fully under attacker control (Scenario S2) costs a schedule-only defence."""
    name = "fixed_interval"

    def __init__(self, T: int):
        self.T = T

    def init_state(self) -> dict:
        return {"last_rotate_t": -self.T}   # so the first rotation lands at t=0, then every T windows

    def decide(self, state: dict, score: float, t: int) -> Action:
        if t - state["last_rotate_t"] >= self.T:
            state["last_rotate_t"] = t
            return "ROTATE"
        return "NONE"


class StaticRulePolicy:
    """Conventional baseline: FIXED, non-adaptive thresholds (no EWMA, no hysteresis by default) — a
    single window above a level reacts immediately. Contrast with AIPolicy's hysteresis shows how a
    naive rule-based system reacts to momentary noise (more false rotations) in the discussion."""
    name = "static_rule"

    def __init__(self, levels: dict, use_hysteresis: bool = False, hysteresis_n: int = 3, hysteresis_k: int = 2):
        self.levels, self.use_hysteresis, self.hn, self.hk = levels, use_hysteresis, hysteresis_n, hysteresis_k

    def init_state(self) -> dict:
        return {"hist": []}

    def decide(self, state: dict, score: float, t: int) -> Action:
        lv = self.levels
        if score >= lv["revoke"]:
            return "REVOKE"
        fire_rotate, fire_warn = score >= lv["rotate"], score >= lv["warn"]
        if self.use_hysteresis:
            h = state["hist"]; h.append(fire_rotate)
            if len(h) > self.hn:
                h.pop(0)
            fire_rotate = sum(h) >= self.hk
        if fire_rotate:
            return "ROTATE"
        return "WARN" if fire_warn else "NONE"


class HybridPolicy:
    """AI trigger PLUS a maximum-key-lifetime safety net: if the wrapped AI policy has not rotated a
    device within max_lifetime_windows, force a ROTATE anyway (defence in depth against a detector miss)."""
    name = "hybrid"

    def __init__(self, ai_policy: AIPolicy, max_lifetime_windows: int = 720):
        self.ai, self.max_lifetime = ai_policy, max_lifetime_windows

    def init_state(self) -> dict:
        s = self.ai.init_state()
        s["lifetime_start_t"] = 0
        return s

    def decide(self, state: dict, score: float, t: int) -> Action:
        action = self.ai.decide(state, score, t)
        if action == "ROTATE":
            state["lifetime_start_t"] = t
            return action
        if action == "REVOKE":
            return action
        if t - state["lifetime_start_t"] >= self.max_lifetime:
            state["lifetime_start_t"] = t
            state["last_rotate_t"], state["in_cooldown_until"] = t, t + self.ai.cooldown
            return "ROTATE"
        return action
