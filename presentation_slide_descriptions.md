# KeyShield-IoT Presentation: Slide-by-Slide Description

Source presentation: [KeyShield_IoT_MTech_Mini_Project_Presentation (1).pptx](<D:/keyshield-iot Final/KeyShield_IoT_MTech_Mini_Project_Presentation (1).pptx>)

## Slide 1 - Title

This is the project title slide for **KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security**. It identifies the two group members, Shreyas Taralekar and Sanket Shitole, the guide Dr. Nivedita Mishra, and the Department of Artificial Intelligence & Machine Learning.

## Slide 2 - Presentation Outline

This slide lists the presentation agenda: team responsibilities, introduction, problem statement, objectives, project plan, literature review, research gap, proposed solution, requirements, technology stack, design and implementation, testing, outcomes, and conclusion.

## Slide 3 - Team and Work Distribution

This slide introduces the project team and their assigned work. Shreyas Taralekar handled the data pipeline, models, and evaluation. Sanket Shitole handled the audit, dashboard, and testing.

## Slide 4 - Introduction

This slide explains **key exposure**, meaning the time a stolen key or compromised device remains trusted. It shows that IoT devices operate continuously, fixed rotation schedules do not reflect current risk, compromised credentials may remain usable, and live evidence can trigger a warning, key rotation, or revocation.

## Slide 5 - Problem Statement

This slide states that long-lived keys increase security exposure and fixed schedules ignore actual attack risk. The main question is whether anomaly-based key rotation can reduce false triggers and restrict attacker traffic. It distinguishes two situations: a stolen key while the defender still controls the device, and an attacker controlling the compromised device.

## Slide 6 - Project Objectives

This slide presents six objectives:

1. Process CICIoT2023 data into 60-second traffic windows.
2. Compare Isolation Forest, One-Class SVM, Autoencoder, and Random Forest models.
3. Calibrate thresholds using benign validation traffic.
4. Implement adaptive, hybrid, and fixed key-rotation policies.
5. Measure key-exposure window (KEW), effective attacker volume (EAV), rotations, and cryptographic cost.
6. Provide a signed, hash-chained audit trail.

## Slide 7 - Project Plan and Timeline

This slide shows the planned 12-week schedule:

- Weeks 1-2: Data
- Weeks 3-4: Models
- Weeks 5-6: Cryptography
- Weeks 7-8: Policy engine
- Weeks 9-10: Evaluation
- Weeks 11-12: Dashboard

## Slide 8 - Literature Review

This slide summarizes four related areas:

- NIST IoT security guidance provides programme-level security recommendations but not runtime anomaly-driven key rotation.
- CICIoT2023 provides IoT attack data and machine-learning benchmarks, but focuses on detection rather than response and exposure metrics.
- NIST SP 800-57 explains key lifecycle and cryptoperiod management, but does not provide automated evidence-driven triggers for IoT fleets.
- TLS 1.3 supports secure sessions and key updates, but refreshes are based on protocol limits or peer requests rather than live anomaly evidence.

## Slide 9 - Research Gap

This slide identifies three gaps and explains how KeyShield-IoT addresses them:

1. **Detection only:** Existing detectors produce scores or novelty decisions. KeyShield-IoT maps those results to warn, rotate, or revoke actions using hysteresis, cooldown, and EWMA.
2. **Fixed schedules:** Existing approaches commonly use cryptoperiods, protocol limits, or peer requests. KeyShield-IoT uses adaptive and hybrid policies, with a maximum-lifetime safeguard in the hybrid policy.
3. **Fragmented evaluation:** Previous work often reports detection quality without exposure, attacker traffic, or cryptographic cost. KeyShield-IoT measures KEW, EAV, rotations per device-hour, and cryptographic cost together across five seeds.

## Slide 10 - Proposed Solution

This slide gives the solution pipeline:

1. Use CICIoT2023 traffic as input.
2. Convert traffic into 60-second feature windows.
3. Detect anomalies using Isolation Forest.
4. Convert detection results into warn, rotate, or revoke decisions.
5. Enforce decisions through key epochs and an audit trail.

## Slide 11 - Requirement Analysis

This slide lists the functional and non-functional requirements.

**Functional requirements:**

- Load and validate CICIoT2023.
- Create 10-flow, 60-second windows.
- Score windows and select actions.
- Rotate or revoke session-key epochs.
- Sign and verify audit events.

**Non-functional requirements:**

- Reproducibility across five seeds.
- Low cryptographic overhead.
- Hash-chained auditability.
- Configurability and maintainability.
- A usable replay dashboard.

## Slide 12 - Technology Stack

This slide identifies the implementation technologies:

- Python 3.13 for implementation.
- Pandas and PyArrow for the data pipeline.
- scikit-learn for Isolation Forest, OCSVM, Autoencoder, and Random Forest models.
- `cryptography` for ECDSA, ECDH, and AES-GCM.
- Streamlit for the interactive dashboard.
- pytest for automated validation.

## Slide 13 - System Design and Architecture

This slide shows the processing architecture:

1. **Data plane:** Load CSV files, clean the data, and create windows.
2. **Detection:** Apply Isolation Forest, OCSVM, and Autoencoder models.
3. **Decision:** Apply hysteresis, cooldown, and EWMA logic.
4. **Enforcement:** Use ECDH, key epochs, and AES-GCM to enforce the selected security action.

## Slide 14 - Development and Implementation

This slide summarizes the implementation stages:

- Clean the data and create device streams.
- Train and score the detection models.
- Build the AI and baseline policy engine.
- Implement secure sessions and signed audit records.
- Build the replay dashboard and metrics.

## Slide 15 - Testing and Debugging

This slide lists the validation areas:

- **Data:** Pool, split, and window integrity.
- **Models:** Training, scoring, and threshold checks.
- **Engine:** Cooldown, hysteresis, and revocation behavior.
- **Cryptography:** AES-GCM operation and audit verification.
- **Dashboard:** Replay behavior and metric rendering.

## Slide 16 - Project Outcome: Detection Performance

This slide reports the main detection results:

- Isolation Forest ROC-AUC: **0.995**
- Isolation Forest PR-AUC: **0.972**
- Episode detection: **1.000**

Category-level results are shown for Isolation Forest, One-Class SVM, and Random Forest:

- DDoS: all three models scored 1.000.
- DoS: all three models scored 1.000.
- Reconnaissance: Isolation Forest 0.865, OCSVM 0.897, Random Forest 0.981.
- Spoofing: Isolation Forest 0.721, OCSVM 0.738, Random Forest 0.977.

The slide also compares policy activity: the adaptive policy produced **0.32 rotations per device-hour**, while the fixed policy with `T=60` produced **1.02 rotations per device-hour**.

## Slide 17 - Conclusion

This slide concludes that evidence-aware key management can reduce exposure while maintaining bounded behavior. It states that Isolation Forest is suitable for unsupervised live detection, adaptive and hybrid policies detected all replayed episodes, and the hybrid policy provides a maximum-lifetime safeguard. Physical deployment and hardware validation are identified as future work.

The slide visually displays page number **19**, although it is the 17th slide in the presentation file.

## Slide 18 - References and Questions

This final slide lists the references used for CICIoT2023, NIST key management, NIST IoT security guidance, Isolation Forest, One-Class SVM, GCM, and TLS 1.3. It ends with “Thank you • Questions?”

The slide visually displays page number **21**, although it is the 18th slide in the presentation file.
