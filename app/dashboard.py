"""Simple interactive KeyShield-IoT replay dashboard."""
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

st.set_page_config(
    page_title="KeyShield-IoT Dashboard",
    layout="wide",
    page_icon=":material/shield:",
)


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
st.caption("See how the system detects an attack and protects IoT devices.")
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
    st.header("Choose a demo")
    source_name = st.radio("Data source", list(sources), key="data_source")
    events = load_events(sources[source_name])

    policies = sorted(events["policy"].unique())
    default_idx = policies.index("ai_demo") if "ai_demo" in policies else (policies.index("ai") if "ai" in policies else 0)
    if source_name == "Scripted demo scenario":
        policy = "ai_demo"
        st.caption("A simple, repeatable demonstration.")
    else:
        policy = st.selectbox("Protection method", policies, index=default_idx, key="policy")
        st.caption("Choose how the system decides to protect devices.")

    by_policy = events[events.policy == policy]
    scenario = st.radio("Attacker scenario", sorted(by_policy["scenario"].unique()),
                        format_func=lambda s: SCENARIO_LABEL.get(s, s), key="scenario")
    by_ps = by_policy[by_policy.scenario == scenario]
    seeds = sorted(by_ps["seed"].astype(str).unique())
    seed = seeds[0] if len(seeds) == 1 else st.selectbox("Seed", seeds, key="seed")
    sub = by_ps[by_ps["seed"].astype(str) == str(seed)].copy()

    devices = sorted(sub["device_id"].unique())
    t_max = int(sub["t"].max())
    t = st.slider("Replay time", 0, t_max, min(t_max, 90), key="window")
    st.caption(f"1 step = 60 seconds · {t_max + 1} total steps")

n_episodes = sub.loc[sub.episode_id >= 0, "device_id"].nunique()
n_events = int((sub.event != "WINDOW").sum())

with st.container(horizontal=True):
    st.metric("Monitored devices", len(devices), border=True)
    st.metric("Devices under attack", n_episodes, border=True)
    st.metric("Security actions", n_events, border=True)

scenario_text = (
    "A stolen key stops working when the key changes."
    if scenario == "S1"
    else "An attacker on a device can reconnect, so the device must be revoked."
)
st.info(scenario_text, title="What happens in this scenario")

st.subheader(f"Device status at step {t}")
now = sub[sub.t == t].set_index("device_id")
card_count = min(len(devices), 5)
for start in range(0, len(devices), card_count):
    cols = st.columns(card_count)
    for col, dev in zip(cols, devices[start:start + card_count]):
        if dev in now.index:
            state = str(now.loc[dev, "fsm_state"])
            score = float(now.loc[dev, "score"])
            epoch = int(now.loc[dev, "epoch"])
        else:
            state, score, epoch = "UNKNOWN", float("nan"), 0
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
                st.caption(f"Risk score: {score:.2f}")
                st.caption(f"Key number: {epoch}")

attacked_devices = sorted(sub.loc[sub.label == 1, "device_id"].unique())
device_sel = attacked_devices[0] if attacked_devices else devices[0]
dsub = sub[sub.device_id == device_sel].sort_values("t")

st.subheader("What happened to the attacked device")
left, right = st.columns(2)
with left:
    st.markdown("**Risk over time**")
    st.line_chart(
        dsub.set_index("t")[["score"]],
        alt=f"Risk score over time for {device_sel}",
        height=250,
    )
with right:
    st.markdown("**Key changes over time**")
    st.line_chart(
        dsub.set_index("t")[["epoch"]],
        alt=f"Key epoch over time for {device_sel}",
        height=250,
        color="#D97706",
    )

with st.expander("View security actions"):
    key_events = dsub[dsub.event != "WINDOW"]
    if len(key_events):
        st.dataframe(
            key_events[["t", "event", "fsm_state", "epoch"]],
            hide_index=True,
            alt=f"Security actions for {device_sel}",
        )
    else:
        st.caption("No security actions have occurred for this device.")

with st.expander("View audit log"):
    audit_path = PROC / "demo_audit_log.jsonl"
    cert_path = PROC / "demo_ca_cert.pem"
    if audit_path.exists() and cert_path.exists():
        entries = [
            json.loads(line)
            for line in audit_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        st.caption(f"{len(entries)} signed and hash-linked audit records")
        if entries:
            st.dataframe(
                pd.DataFrame(entries)[["device_id", "event", "epoch", "reason", "ts"]],
                hide_index=True,
                alt="Signed audit log",
            )
        if st.button("Verify audit log", icon=":material/check_circle:", type="primary", key="verify_audit"):
            ok, bad = verify_audit(entries, cert_path.read_bytes())
            if ok:
                st.success("Verified: every record and signature is valid.")
            else:
                st.error(f"Verification failed at record {bad}.")
    else:
        st.info("Run `python -m src.sim.make_demo` to generate the audit demonstration.")

st.caption("KeyShield-IoT · AI for Cyber Security (TEE7263) · Mini project")
