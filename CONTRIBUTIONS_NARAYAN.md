# Project Contributions: Stream Mining & Advanced Analytics
**Contributor**: Narayan Anshu

## Overview
This document details the implementation of advanced **Stream Mining** techniques integrated into the NT-SCADA system. The work focuses on moving beyond static anomaly detection to dynamic, adaptive real-time analytics using open-source technologies.

## Key Contributions

### 1. Advanced Stream Mining Architecture
Designed and implemented a **Sidecar Architecture** for the mining engine.
- **Innovation**: Decoupled the advanced analytics from the critical path.
- **Benefit**: Ensures zero latency impact on the main SCADA control loop while enabling complex computation.
- **Implementation**: `nt-scada/stream/stream_miner.py`

### 2. Open Source Technology Integration
Integrated cutting-edge open-source libraries to enhance system intelligence:
- **River (Online ML)**: Integrated the `river` library for incremental learning. Unlike traditional batch ML (scikit-learn), this allows the model to learn from every single data point in real-time.
- **Apache Kafka**: Leveraged Kafka Consumer Groups to enable parallel processing of the same data stream for different purposes (Control vs. Mining).

### 3. Implemented Techniques

#### A. Concept Drift Detection (ADWIN)
- **Problem**: Physical sensors degrade, and environments change. Static thresholds (e.g., `if value > 50`) become obsolete, leading to false alarms.
- **Solution**: Implemented **ADWIN (ADaptive WINdowing)**.
- **Function**: Automatically detects when the statistical distribution of data changes (drifts) and flags it for review.

#### B. Online / Incremental Learning
- **Problem**: Batch-trained models are outdated the moment they are deployed.
- **Solution**: Implemented **Hoeffding Trees**.
- **Function**: A decision tree that updates its structure with each incoming sample, allowing the system to "learn" new normal operating states or attack patterns on the fly.

#### C. Real-time Rolling Statistics
- **Function**: Calculates sliding window variance and means to detect instability before it breaches absolute limits.

## Artifacts Created
- `nt-scada/stream/stream_miner.py`: The Python-based stream mining engine.
- `nt-scada/stream/STREAM_MINING_ROADMAP.md`: A strategic roadmap for future analytics capabilities.
- `nt-scada/requirements.txt`: Updated dependencies to include `river`.

