# KeyShield-IoT

AI-driven adaptive key rotation for IoT security. The system combines anomaly detection,
certificate management, key rotation, revocation, quarantine, and a hash-chained signed audit log.

## Run the live dashboard

```powershell
cd "D:\keyshield-iot Final"
.venv\Scripts\activate
streamlit run app/dashboard.py
```

The dashboard automatically creates a deterministic demo and works without real experiment files.
It includes device-state replay, anomaly timelines, key epochs, S1/S2 exposure metrics, and
ECDSA audit-log verification.

## Setup

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Merged CICIoT2023 data

Place the downloaded MERGED CSV files here:

```text
data/raw/Merged01.csv
data/raw/Merged02.csv
data/raw/Merged03.csv
data/raw/Merged04.csv
data/raw/Merged05.csv
data/raw/Merged06.csv
```

Inspect and build the real dataset:

```powershell
python -m src.data.inspect_data
python -m src.data.build_dataset --force
```

The current 6-file dataset contains 4,297,838 rows. With the default configuration, benign rows
are reused as needed to reach the configured simulated stream size.

## Generate demo and run

```powershell
python -m src.sim.make_demo
streamlit run app/dashboard.py
```

## Full real-data pipeline

```powershell
python -m src.models.train
python -m src.models.evaluate
python -m src.crypto.benchmark
python -m src.engine.calibrate
python -m src.sim.run_sim --all
python -m src.eval.e3_report
```

## Tests

```powershell
pytest -q
```

## Project structure

```text
app/          Streamlit dashboard
configs/      Dataset, model, engine, and demo settings
data/raw/     Downloaded CICIoT2023 MERGED CSV files
data/processed/ Generated Parquet, scores, streams, and demo logs
src/data/     CSV loading, cleaning, splitting, and streams
src/models/   Isolation Forest, One-Class SVM, Autoencoder, and RF reference
src/crypto/   CA, sessions, key management, and signed audit log
src/engine/   AI and fallback policies plus mitigation state machine
src/sim/      Demo and full experiment replay
src/eval/     KEW, EAV, cost metrics, and E3 report
tests/        Automated test suite
```

## Important project limitations

- This project uses replayed CICIoT2023 network traffic, not physical IoT hardware.
- The attack timeline and dashboard device data are simulated.
- The demo is deterministic and is separate from measured real-experiment results.
- Web-based and brute-force categories have low support and are excluded from the experiment.
- Baseline IoT security hygiene is assumed: secure credentials, patched firmware, segmentation,
  and disabled unused services.
