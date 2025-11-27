# Stream Mining Techniques Roadmap

Based on the current implementation of NT-SCADA (which utilizes Kafka, Flink, and Python-based stream processing), here are advanced **Stream Mining** techniques to enhance the system's analytical capabilities.

## 1. Concept Drift Detection
**Current State**: The system uses static thresholds (e.g., `value < 20`) or batch-calculated statistics (Z-Score based on historical mean).
**Problem**: Physical systems change over time (wear and tear, seasonal changes). Static models become obsolete ("drift").
**Proposed Technique**: Implement **ADWIN (ADaptive WINdowing)** or **KSWIN (Kolmogorov-Smirnov Windowing)**.
- **How it works**: Automatically detects when the statistical distribution of the data stream changes.
- **Implementation**: 
  - Use the Python `river` library in `stream_processor.py`.
  - When drift is detected, automatically trigger a model retraining pipeline or adjust thresholds.

## 2. Online / Incremental Learning
**Current State**: Models are trained in batch (Phase 3) and applied to streams.
**Problem**: The model doesn't learn from new data until the next batch retrain.
**Proposed Technique**: Use **Hoeffding Trees** or **Adaptive Random Forests**.
- **How it works**: The model updates its internal structure with each incoming sample (or mini-batch) without needing to store all historical data.
- **Implementation**:
  - Integrate `river.tree.HoeffdingTreeClassifier` into the Python stream processor.
  - Allows the SCADA system to adapt to new attack patterns or operating states instantly.

## 3. Sliding Window Statistics (Complex Event Processing)
**Current State**: Anomaly detection is point-wise (checks one value at a time).
**Problem**: Single spikes might be noise. Real anomalies often manifest as trends over time (e.g., "temperature rising for 5 consecutive minutes").
**Proposed Technique**: **Sliding Window Aggregations**.
- **How it works**: Maintain a window of the last $N$ seconds or $K$ events. Calculate rolling mean, variance, or rate of change.
- **Implementation**:
  - **Flink**: Use `window(TumblingEventTimeWindows.of(Time.seconds(60)))`.
  - **Python**: Use `collections.deque` to maintain a buffer and calculate `np.std()` or `np.mean()` dynamically.

## 4. Unsupervised Online Clustering
**Current State**: Classification relies on predefined categories (LOW, HIGH, etc.).
**Problem**: New, undefined operating states (e.g., "Startup Phase", "Maintenance Mode") are misclassified.
**Proposed Technique**: **Stream Clustering (e.g., DenStream, CluStream)**.
- **How it works**: Groups incoming data points into micro-clusters in real-time. Outliers that don't fit any cluster are potential anomalies or new states.
- **Implementation**:
  - Use `river.cluster.DBSTREAM` to detect density-based clusters in the sensor data stream.

## 5. Symbolic Aggregate approXimation (SAX)
**Proposed Technique**: Convert continuous sensor streams into string patterns (e.g., "abcba").
- **Why**: Allows for regex-like pattern matching on sensor data (e.g., detect "heartbeat" patterns or specific failure signatures).

## Recommended Next Steps
1. **Add `river` dependency**: `pip install river`
2. **Upgrade `stream_processor.py`**:
   - Implement a `DriftDetector` class using `river.drift.ADWIN`.
   - Replace static `detect_anomaly` with an adaptive scorer like `river.anomaly.HalfSpaceTrees`.
3. **Enhance `flink_job.py`**:
   - Add a Window function to calculate the rate of change (derivative) of sensor values to detect rapid drops/spikes that are within absolute limits but physically impossible.
