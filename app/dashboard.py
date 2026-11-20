"""Interactive KeyShield-IoT replay dashboard."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so `import src...` works regardless of cwd

from src.eval.kew import episodes_kew_eav  # noqa: E402
from src.config import ROOT, load_config  # noqa: E402
from src.sim.make_demo import run as generate_demo_run  # noqa: E402

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
STATE_COLORS = {"NORMAL": "#1fb97d", "SUSPECT": "#e0a52c", "ROTATED": "#3a8bd8",
               "QUARANTINED": "#e14b5a", "RECOVERED": "#7c5be8"}
SCENARIO_LABEL = {"S1": "S1 — key theft", "S2": "S2 — device compromise"}

st.set_page_config(page_title="KeyShield-IoT Dashboard", layout="wide", page_icon="🛡️")


@st.cache_data
def load_events(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)

@st.cache_data
def verify_audit(entries: list[dict], cert_bytes: bytes) -> tuple[bool, int | None]:
    from cryptography import x509
    from src.crypto.audit_log import verify_entries
    cert = x509.load_pem_x509_certificate(cert_bytes)
    return verify_entries(entries, cert.public_key())


def ensure_demo() -> bool:
    demo_path = PROC / "demo_events.parquet"
    if demo_path.exists():
        return True
    try:
        dcfg = load_config(ROOT / "configs" / "demo.yaml")
        generate_demo_run(dcfg, PROC)
        return demo_path.exists()
    except Exception as exc:
        st.error(f"Could not generate the demo: {exc}")
        return False


st.title("KeyShield-IoT", icon=":material/shield:")
st.caption("AI-driven adaptive key rotation and certificate response for IoT devices")
ensure_demo()

demo_path, real_path = PROC / "demo_events.parquet", PROC / "events.parquet"
sources = {}
if demo_path.exists():
    sources["Scripted demo scenario"] = demo_path
if real_path.exists():
    sources["Real experiment results"] = real_path
if not sources:
    st.error("No event log found. Run `python -m src.sim.make_demo` "
             "and/or `python -m src.sim.run_sim --all` first, then reload this page.")
    st.stop()

with st.sidebar:
    st.header("Experiment controls")
    source_name = st.radio("Data source", list(sources), key="data_source")
    events = load_events(sources[source_name])
    if source_name == "Scripted demo scenario":
        st.caption("Hand-scripted, deterministic demonstration.")
    else:
        st.caption("Results from a completed experiment run.")

    policies = sorted(events["policy"].unique())
    default_idx = policies.index("ai_demo") if "ai_demo" in policies else (policies.index("ai") if "ai" in policies else 0)
    policy = st.selectbox("Policy", policies, index=default_idx, key="policy")

    by_policy = events[events.policy == policy]
    scenario = st.radio("Attacker scenario", sorted(by_policy["scenario"].unique()),
                        format_func=lambda s: SCENARIO_LABEL.get(s, s), key="scenario")
    by_ps = by_policy[by_policy.scenario == scenario]
    seeds = sorted(by_ps["seed"].astype(str).unique())
    seed = seeds[0] if len(seeds) == 1 else st.selectbox("Seed", seeds, key="seed")
    sub = by_ps[by_ps["seed"].astype(str) == str(seed)].copy()

    devices = sorted(sub["device_id"].unique())
    t_max = int(sub["t"].max())
    t = st.slider("Window", 0, t_max, min(t_max, 90), key="window")
    st.caption(f"{len(devices)} device(s) · {t_max + 1} windows · 1 window = 60s")

overview, timeline, audit = st.tabs(
    ["Overview", "Device timeline", "Audit trail"],
    on_change="rerun",
)

with overview:
    n_episodes = sub.loc[sub.episode_id >= 0, "device_id"].nunique()
    n_events = int((sub.event != "WINDOW").sum())
    with st.container(horizontal=True):
        st.metric("Devices", len(devices), border=True)
        st.metric("Compromise episodes", n_episodes, border=True)
        st.metric("Security events", n_events, border=True)
        st.metric("Current window", t, delta=f"{t * 60}s elapsed", border=True)

    st.subheader(f"Device status at window {t}", icon=":material/monitor_heart:")
    now = sub[sub.t == t].set_index("device_id")
    state_cards = []
    for dev in devices:
        if dev in now.index:
            state = str(now.loc[dev, "fsm_state"])
            score = float(now.loc[dev, "score"])
            epoch = int(now.loc[dev, "epoch"])
        else:
            state, score, epoch = "UNKNOWN", float("nan"), 0
        state_cards.append((dev, state, score, epoch))

    card_count = min(len(state_cards), 5)
    for start in range(0, len(state_cards), card_count):
        cols = st.columns(card_count)
        for col, (dev, state, score, epoch) in zip(cols, state_cards[start:start + card_count]):
            with col:
                with st.container(border=True, height="stretch"):
                    st.markdown(f"**{dev}**")
                    st.badge(state, color={
                        "NORMAL": "green",
                        "SUSPECT": "orange",
                        "ROTATED": "blue",
                        "QUARANTINED": "red",
                        "RECOVERED": "violet",
                    }.get(state, "gray"))
                    st.caption(f"Score {score:.2f} · Epoch {epoch}")

    st.caption("S1 ends exposure on rotation or revocation. S2 ends exposure only on revocation.")

if timeline.open:
    with timeline:
        attacked_devices = sorted(sub.loc[sub.label == 1, "device_id"].unique())
        default_dev = attacked_devices[0] if attacked_devices else devices[0]
        device_sel = st.selectbox(
            "Device",
            devices,
            index=devices.index(default_dev),
            key="device_inspector",
        )
        dsub = sub[sub.device_id == device_sel].sort_values("t")

        left, right = st.columns(2)
        with left:
            st.subheader("Anomaly score", icon=":material/analytics:")
            st.line_chart(
                dsub.set_index("t")[["score"]],
                alt=f"Anomaly score over time for {device_sel}",
                height=280,
            )
        with right:
            st.subheader("Key epoch", icon=":material/vpn_key:")
            st.line_chart(
                dsub.set_index("t")[["epoch"]],
                alt=f"Key epoch over time for {device_sel}",
                height=280,
                color="#D97706",
            )

        key_events = dsub[dsub.event != "WINDOW"]
        st.subheader("Security events")
        if len(key_events):
            st.dataframe(
                key_events[["t", "event", "fsm_state", "epoch", "label"]],
                hide_index=True,
                alt=f"Security event table for {device_sel}",
            )
        else:
            st.caption("No security events are recorded for this device in the selected run.")

        st.subheader("Key exposure window")
        windows_per_device = int(sub["t"].max()) + 1
        ep = episodes_kew_eav(by_policy, windows_per_device=windows_per_device, seconds_per_window=60)
        ep_d = ep[ep.device_id == device_sel]
        if len(ep_d):
            ep_d = ep_d.copy()
            ep_d["scenario"] = ep_d["scenario"].map(SCENARIO_LABEL).fillna(ep_d["scenario"])
            chart_col, table_col = st.columns([1, 2])
            with chart_col:
                st.bar_chart(
                    ep_d.set_index("scenario")[["kew_seconds"]],
                    alt="Key exposure window by attacker scenario",
                    height=280,
                )
            with table_col:
                show = ep_d[
                    ["scenario", "onset_t", "detection_t", "censored",
                     "kew_seconds", "eav_windows", "category"]
                ]
                st.dataframe(show, hide_index=True, alt="Key exposure metrics by scenario")
        else:
            st.info("The selected device has no compromise episode in this run.")

if audit.open:
    with audit:
        st.subheader("Signed audit log", icon=":material/verified:")
        audit_path = PROC / "demo_audit_log.jsonl"
        cert_path = PROC / "demo_ca_cert.pem"
        if audit_path.exists() and cert_path.exists():
            entries = [
                json.loads(line)
                for line in audit_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            st.caption(
                f"{len(entries)} hash-chained, ECDSA-signed entries"
                + (f" for {entries[0]['device_id']}" if entries else "")
            )
            if entries:
                st.dataframe(
                    pd.DataFrame(entries)[["device_id", "event", "epoch", "reason", "ts"]],
                    hide_index=True,
                    alt="Persisted hash-chained signed audit entries",
                )
            if st.button("Verify chain", icon=":material/check_circle:", type="primary", key="verify_audit"):
                ok, bad = verify_audit(entries, cert_path.read_bytes())
                if ok:
                    st.success("Chain verified: every hash link and ECDSA signature is valid.")
                else:
                    st.error(f"Chain verification failed at entry {bad}.")
        else:
            st.info("Run `python -m src.sim.make_demo` to generate the audit demonstration.")

st.caption("KeyShield-IoT · AI for Cyber Security (TEE7263) · Mini project")
