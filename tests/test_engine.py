"""Batch 4 tests: calibration, the 4 policies, and every edge of the mitigation state machine."""
import numpy as np
import pytest

from src.engine.calibrate import compute_thresholds
from src.engine.mitigation import DeviceFSM
from src.engine.mock_key_manager import MockKeyManager
from src.engine.policies import AIPolicy, FixedIntervalPolicy, HybridPolicy, StaticRulePolicy

LEVELS = {"warn": 1.0, "rotate": 2.0, "revoke": 3.0}


def test_calibration_orders_levels_and_uses_only_given_scores():
    rng = np.random.default_rng(0)
    benign = rng.normal(0, 1, 5000)
    t = compute_thresholds(benign, {"warn": 0.95, "rotate": 0.99, "revoke": 0.999})
    assert t["warn"] < t["rotate"] < t["revoke"] and t["n_benign_windows"] == 5000
    # sparse data: revoke must still be enforced above rotate by the margin
    tiny = np.array([1.0, 1.0, 1.0, 5.0])
    t2 = compute_thresholds(tiny, {"warn": 0.5, "rotate": 0.9, "revoke": 0.95}, min_revoke_margin=1.2)
    assert t2["revoke"] >= t2["rotate"] * 1.2 - 1e-9


def test_ai_policy_ignores_isolated_noise_but_fires_on_sustained_anomaly():
    p = AIPolicy(LEVELS, hysteresis_n=3, hysteresis_k=2, cooldown_windows=10, revoke_persist_windows=100,
                fast_path_multiplier=10)   # fast path disabled (very high) to isolate hysteresis behaviour
    st = p.init_state()
    seq = [0.1, 0.1, 2.5, 0.1, 0.1, 0.1, 2.5, 2.5, 0.1]   # one isolated spike, then a real 2-of-3 run
    acts = [p.decide(st, s, t) for t, s in enumerate(seq)]
    assert acts[2] in ("WARN", "NONE") and acts[2] != "ROTATE"   # isolated spike never rotates
    assert "ROTATE" in acts[6:8]                                  # sustained anomaly eventually rotates


def test_ai_policy_fast_path_bypasses_hysteresis():
    p = AIPolicy(LEVELS, hysteresis_n=5, hysteresis_k=5, fast_path_multiplier=1.5)
    st = p.init_state()
    assert p.decide(st, LEVELS["rotate"] * 1.6, 0) == "ROTATE"   # fires on the very first window


def test_ai_policy_cooldown_then_persistence_revokes():
    p = AIPolicy(LEVELS, hysteresis_n=1, hysteresis_k=1, cooldown_windows=5, revoke_persist_windows=3,
                fast_path_multiplier=10)
    st = p.init_state()
    assert p.decide(st, 2.5, 0) == "ROTATE"               # streak=1 (the rotate window itself)
    assert p.decide(st, 2.5, 1) in ("WARN", "NONE")        # cooldown blocks a second ROTATE; streak=2
    assert p.decide(st, 2.5, 2) == "REVOKE"                # streak=3 >= revoke_persist_windows -> escalate


def test_ai_policy_sustained_severe_score_does_not_rotate_every_window_before_escalating():
    """Regression test for a real bug: a sustained severe score (>= rotate_level * fast_path_multiplier)
    used to re-trigger the fast path on EVERY window (it only checked t - last_rotate_t >= 1, not
    cooldown), rotating forever and never letting the persistence counter reach revoke_persist_windows.
    Fixed: the fast path now also requires `not in_cooldown`. Checked over exactly the cooldown span,
    since once cooldown naturally elapses the bare policy (with no FSM) has no memory of having already
    escalated — that part is the FSM's job, tested separately below."""
    p = AIPolicy(LEVELS, hysteresis_n=3, hysteresis_k=2, cooldown_windows=5, revoke_persist_windows=3,
                fast_path_multiplier=1.5)
    st = p.init_state()
    severe = LEVELS["rotate"] * 1.6
    acts = [p.decide(st, severe, t) for t in range(5)]   # exactly one cooldown window
    assert acts[0] == "ROTATE"
    assert "REVOKE" in acts[1:], f"sustained severity never escalated to REVOKE within cooldown: {acts}"
    first_revoke = acts.index("REVOKE")
    assert acts[1:first_revoke].count("ROTATE") == 0, f"fast path re-fired before escalation: {acts}"


def test_fsm_absorbs_renewed_rotate_proposals_after_revoke_even_under_sustained_severe_score():
    """The realistic, integrated version of the fix above: once the FSM has quarantined a device, it does
    not matter that the bare policy might later propose ROTATE again (e.g. the fast path re-arming after
    its own cooldown elapses) — the FSM ignores every proposal until an explicit recover()."""
    p = AIPolicy(LEVELS, hysteresis_n=3, hysteresis_k=2, cooldown_windows=5, revoke_persist_windows=3,
                fast_path_multiplier=1.5)
    st = p.init_state()
    km, fsm = MockKeyManager(), DeviceFSM("dX")
    km.enroll("dX")
    severe = LEVELS["rotate"] * 1.6
    for t in range(10):
        fsm.apply(p.decide(st, severe, t), t, km, cooldown_windows=5)
    assert fsm.state == "QUARANTINED"
    assert km.n_calls("revoke") == 1
    assert km.n_calls("rotate") == 1, "exactly one real rotation should ever reach the key manager"


def test_fixed_interval_ignores_score_and_never_revokes():
    p = FixedIntervalPolicy(T=5)
    st = p.init_state()
    acts = [p.decide(st, 0.0, t) for t in range(16)]   # score is always 0 (benign-looking)
    assert [t for t, a in enumerate(acts) if a == "ROTATE"] == [0, 5, 10, 15]   # purely on schedule
    assert "REVOKE" not in acts


def test_static_rule_reacts_to_a_single_window_no_hysteresis():
    p = StaticRulePolicy(LEVELS, use_hysteresis=False)
    st = p.init_state()
    assert p.decide(st, 2.5, 0) == "ROTATE"     # one window above rotate_level is enough, unlike AIPolicy
    assert p.decide(st, 3.5, 1) == "REVOKE"


def test_static_rule_hysteresis_variant_matches_ai_robustness():
    p = StaticRulePolicy(LEVELS, use_hysteresis=True, hysteresis_n=3, hysteresis_k=2)
    st = p.init_state()
    assert p.decide(st, 2.5, 0) != "ROTATE"     # a single spike no longer rotates once hysteresis is on


def test_hybrid_forces_rotation_after_max_lifetime_even_without_anomaly():
    ai = AIPolicy(LEVELS, hysteresis_n=3, hysteresis_k=3, cooldown_windows=5)
    p = HybridPolicy(ai, max_lifetime_windows=10)
    st = p.init_state()
    acts = [p.decide(st, 0.1, t) for t in range(11)]    # score always benign; AI alone would never rotate
    assert acts[10] == "ROTATE" and acts.count("ROTATE") == 1


def test_hybrid_still_lets_ai_rotate_early_and_resets_the_lifetime_clock():
    ai = AIPolicy(LEVELS, hysteresis_n=1, hysteresis_k=1, cooldown_windows=3, fast_path_multiplier=1.5)
    p = HybridPolicy(ai, max_lifetime_windows=10)
    st = p.init_state()
    assert p.decide(st, LEVELS["rotate"] * 1.6, 2) == "ROTATE"   # AI rotates early at t=2
    assert st["lifetime_start_t"] == 2                            # safety-net clock restarts from there


# ---- mitigation state machine: one test per transition edge, plus the full named path ----

def test_fsm_full_named_path_normal_to_recovered_to_normal():
    km = MockKeyManager()
    km.enroll("d1")
    fsm = DeviceFSM("d1")
    assert fsm.apply("WARN", 0, km, cooldown_windows=5) == "SUSPECT"
    assert fsm.apply("ROTATE", 1, km, cooldown_windows=5) == "ROTATED"
    assert km.n_calls("rotate") == 1
    assert fsm.apply("REVOKE", 2, km, cooldown_windows=5) == "QUARANTINED"
    assert km.n_calls("revoke") == 1
    fsm.recover(10)
    assert fsm.state == "NORMAL"
    path = [h[3] for h in fsm.history]
    assert path == ["SUSPECT", "ROTATED", "QUARANTINED", "RECOVERED", "NORMAL"]


def test_fsm_suspect_recovers_to_normal_without_rotating():
    km = MockKeyManager(); fsm = DeviceFSM("d2")
    fsm.apply("WARN", 0, km, cooldown_windows=5, recover_after=3)
    for t in range(1, 5):             # 4 clean windows: recovers once t - suspect_clean_since >= recover_after
        fsm.apply("NONE", t, km, cooldown_windows=5, recover_after=3)
    assert fsm.state == "NORMAL" and km.n_calls("rotate") == 0


def test_fsm_rotated_dwell_blocks_a_second_physical_rotate_until_cooldown_elapses():
    km = MockKeyManager(); fsm = DeviceFSM("d3")
    fsm.apply("ROTATE", 0, km, cooldown_windows=5)
    assert fsm.state == "ROTATED" and km.n_calls("rotate") == 1
    for t in range(1, 5):
        fsm.apply("ROTATE", t, km, cooldown_windows=5)   # policy keeps proposing; FSM must not re-call rotate
    assert km.n_calls("rotate") == 1
    fsm.apply("NONE", 5, km, cooldown_windows=5)          # cooldown has elapsed (t >= dwell_until)
    assert fsm.state == "NORMAL"


def test_fsm_direct_normal_to_quarantined_on_revoke():
    km = MockKeyManager(); fsm = DeviceFSM("d4")
    assert fsm.apply("REVOKE", 0, km, cooldown_windows=5) == "QUARANTINED"
    assert km.n_calls("revoke") == 1 and km.n_calls("rotate") == 0


def test_fsm_quarantined_ignores_further_proposals_until_recover():
    km = MockKeyManager(); fsm = DeviceFSM("d5")
    fsm.apply("REVOKE", 0, km, cooldown_windows=5)
    for t, action in enumerate(["ROTATE", "WARN", "REVOKE", "NONE"], start=1):
        fsm.apply(action, t, km, cooldown_windows=5)
    assert fsm.state == "QUARANTINED" and km.n_calls("revoke") == 1 and km.n_calls("rotate") == 0
    with pytest.raises(ValueError):
        DeviceFSM("d6").recover(0)   # cannot recover a device that was never quarantined


def test_fsm_rotated_can_still_escalate_to_quarantined_on_persistent_revoke():
    km = MockKeyManager(); fsm = DeviceFSM("d7")
    fsm.apply("ROTATE", 0, km, cooldown_windows=10)
    assert fsm.apply("REVOKE", 3, km, cooldown_windows=10) == "QUARANTINED"
    assert km.n_calls("rotate") == 1 and km.n_calls("revoke") == 1


def test_end_to_end_ai_policy_plus_real_key_manager_integration():
    """Bridges Batch 3 (real crypto) and Batch 4 (policy + FSM) on one synthetic score sequence."""
    from src.crypto.key_manager import KeyManager
    km = KeyManager()
    km.enroll("dev_live")
    policy = AIPolicy(LEVELS, hysteresis_n=1, hysteresis_k=1, cooldown_windows=3, fast_path_multiplier=1.5)
    fsm, st = DeviceFSM("dev_live"), policy.init_state()
    scores = [0.1, 0.1, 2.5, 0.1, 0.1, 0.1]
    for t, s in enumerate(scores):
        fsm.apply(policy.decide(st, s, t), t, km, cooldown_windows=3)
    assert fsm.state in ("ROTATED", "NORMAL")
    blob = km.encrypt("dev_live", b"post-rotation message")
    assert km.decrypt("dev_live", blob) == b"post-rotation message"
