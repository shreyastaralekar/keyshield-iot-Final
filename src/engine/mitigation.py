"""The mitigation state machine. A policy's decide() only PROPOSES an action; this FSM decides whether
to actually call the key manager and tracks each device's lifecycle: NORMAL, SUSPECT, ROTATED,
QUARANTINED, RECOVERED.

Transition table (also see tests/test_engine.py, one test per edge):
  NORMAL     --WARN-->    SUSPECT
  NORMAL     --ROTATE-->  ROTATED      (km.rotate called)
  NORMAL     --REVOKE-->  QUARANTINED  (km.revoke called)
  SUSPECT    --NONE, for recover_after windows--> NORMAL
  SUSPECT    --ROTATE-->  ROTATED      (km.rotate called)
  SUSPECT    --REVOKE-->  QUARANTINED  (km.revoke called)
  ROTATED    --(cooldown_windows elapse with no further WARN/ROTATE/REVOKE)--> NORMAL
  ROTATED    --REVOKE-->  QUARANTINED  (km.revoke called; persistence despite rotation)
  QUARANTINED --recover() [explicit, never automatic]--> RECOVERED --(immediately)--> NORMAL

Once QUARANTINED, further decide() proposals are IGNORED until recover() is called explicitly — a
quarantined device does not keep calling rotate/revoke on the key manager.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts import Action

States = str  # "NORMAL" | "SUSPECT" | "ROTATED" | "QUARANTINED" | "RECOVERED"


@dataclass
class DeviceFSM:
    device_id: str
    state: States = "NORMAL"
    dwell_until: int = -1          # ROTATED state holds until this window index
    suspect_clean_since: int = -1  # first window, while SUSPECT, that saw no WARN
    history: list = field(default_factory=list)   # (t, action_proposed, state_before, state_after)

    def apply(self, action: Action, t: int, km, cooldown_windows: int, recover_after: int = 5) -> States:
        before = self.state
        if self.state == "QUARANTINED":
            action = "NONE"       # ignore all proposals while quarantined; recover() is the only way out
        elif self.state == "ROTATED":
            # Dwelling in the post-rotation cooldown: REVOKE can still escalate (persistence despite
            # rotation), but a repeated ROTATE/WARN/NONE proposal is absorbed here, not re-applied below —
            # this is what stops the FSM from calling km.rotate() again on every window of the cooldown.
            if action == "REVOKE":
                km.revoke(self.device_id, reason="policy_revoke")
                self.state = "QUARANTINED"
            elif t >= self.dwell_until:
                self.state = "NORMAL"   # cooldown elapsed; the NEXT call will process a fresh proposal
            # else: stay ROTATED, no key-manager call
        elif action == "REVOKE":
            km.revoke(self.device_id, reason="policy_revoke")
            self.state = "QUARANTINED"
        elif action == "ROTATE":
            km.rotate(self.device_id, reason="policy_rotate")
            self.state, self.dwell_until = "ROTATED", t + cooldown_windows
        elif action == "WARN":
            if self.state == "NORMAL":
                self.state = "SUSPECT"
            self.suspect_clean_since = -1
        elif self.state == "SUSPECT":       # action is NONE while SUSPECT
            if self.suspect_clean_since < 0:
                self.suspect_clean_since = t
            if t - self.suspect_clean_since >= recover_after:
                self.state = "NORMAL"
        self.history.append((t, action, before, self.state))
        return self.state

    def recover(self, t: int) -> None:
        """Explicit, human-triggered re-enrolment of a quarantined device. Never called automatically."""
        if self.state != "QUARANTINED":
            raise ValueError(f"{self.device_id} is not QUARANTINED (state={self.state})")
        self.state = "RECOVERED"
        self.history.append((t, "RECOVER", "QUARANTINED", "RECOVERED"))
        self.state = "NORMAL"
        self.history.append((t, "RECOVER", "RECOVERED", "NORMAL"))
