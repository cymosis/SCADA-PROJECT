"""
NT-SCADA Batch Processing with Apache Flink
Professional batch analytics and ML model training pipeline
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

from models.model_registry import ModelRegistry

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScadaDataLoader:
    """Load SCADA data from InfluxDB"""

    def __init__(
        self,
        url: str = "http://influxdb:8086",
        token: str = "nt-scada-token-secret-key-12345",
        org: str = "nt-scada",
        bucket: str = "scada_data",
    ):
        """
        Initialize data loader.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client: InfluxDBClient = None
        self.query_api: QueryApi = None

    def connect(self) -> bool:
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.query_api = self.client.query_api()
            self.client.ping()
            logger.info("Connected to InfluxDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False

    def load_sensor_data(
        self,
        days: int = 7,
        measurement: str = "sensor_data",
    ) -> pd.DataFrame:
        """
        Load sensor data from InfluxDB.
        
        Args:
            days: Number of days to load
            measurement: Measurement name
            
        Returns:
            DataFrame with sensor data
        """
        if not self.client:
            raise RuntimeError("Not connected to InfluxDB")

        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: -{days}d)
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

        try:
            result = self.query_api.query(query)
            records = []

            for table in result:
                for record in table.records:
                    records.append(
                        {
                            "timestamp": record.get_time(),
                            "sensor_id": record.values.get("sensor_id"),
                            "value": record.get_value(),
                            "anomaly": record.values.get("anomaly", 0),
                            "severity": record.values.get("severity"),
                            "category": record.values.get("category"),
                        }
                    )

            df = pd.DataFrame(records)
            logger.info(f"Loaded {len(df)} sensor records")
            return df

        except Exception as e:
            logger.error(f"Error loading sensor data: {e}")
            return pd.DataFrame()

    def close(self) -> None:
        """Close InfluxDB connection"""
        if self.client:
            self.client.close()


class FeatureEngineer:
    """Feature engineering for SCADA data"""

    @staticmethod
    def create_time_based_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["day_of_month"] = df["timestamp"].dt.day
        
        return df

    @staticmethod
    def create_statistical_features(
        df: pd.DataFrame,
        window_sizes: List[int] = [5, 10, 30],
    ) -> pd.DataFrame:
        """Create statistical rolling window features"""
        df = df.copy()
        df = df.sort_values("timestamp")
        
        for window in window_sizes:
            df[f"rolling_mean_{window}"] = (
                df.groupby("sensor_id")["value"].transform(
                    lambda x: x.rolling(window=window, min_periods=1).mean()
                )
            )
            df[f"rolling_std_{window}"] = (
                df.groupby("sensor_id")["value"].transform(
                    lambda x: x.rolling(window=window, min_periods=1).std()
                )
            )
            df[f"rolling_min_{window}"] = (
                df.groupby("sensor_id")["value"].transform(
                    lambda x: x.rolling(window=window, min_periods=1).min()
                )
            )
            df[f"rolling_max_{window}"] = (
                df.groupby("sensor_id")["value"].transform(
                    lambda x: x.rolling(window=window, min_periods=1).max()
                )
            )
        
        return df

    @staticmethod
    def create_statistical_aggregates(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create statistical aggregates per sensor"""
        aggregates = df.groupby("sensor_id")["value"].agg([
            ("mean", "mean"),
            ("std", "std"),
            ("min", "min"),
            ("max", "max"),
            ("median", "median"),
            ("skew", "skew"),
            ("kurtosis", "kurtosis"),
        ]).reset_index()
        
        aggregates.columns = ["sensor_id"] + [f"agg_{col}" for col in aggregates.columns[1:]]
        return aggregates

    @staticmethod
    def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """Complete feature engineering pipeline"""
        logger.info("Engineering features...")
        
        df = FeatureEngineer.create_time_based_features(df)
        df = FeatureEngineer.create_statistical_features(df)
        
        df = df.fillna(df.mean(numeric_only=True))
        df = df.dropna()
        
        logger.info(f"Features engineered. Shape: {df.shape}")
        return df


class BinaryClassifierTrainer:
    """Train binary classification model"""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None

    def prepare_data(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        feature_cols = [
            col for col in df.columns
            if col not in ["timestamp", "sensor_id", "anomaly", "severity", "category"]
        ]
        self.feature_names = feature_cols
        
        X = df[feature_cols].values
        y = df["anomaly"].values
        
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        
        return X_train, X_test, y_train, y_test

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train binary classifier"""
        logger.info("Training binary classifier...")
        
        X_train, X_test, y_train, y_test = self.prepare_data(df)
        
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=self.random_state,
            n_jobs=-1,
            class_weight="balanced",
        )
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred)),
            "recall": float(recall_score(y_test, y_pred)),
            "f1": float(f1_score(y_test, y_pred)),
            "roc_auc": float(roc_auc_score(y_test, y_pred_proba)),
        }
        
        logger.info(f"Binary classifier metrics: {metrics}")
        
        return {
            "model": self.model,
            "scaler": self.scaler,
            "metrics": metrics,
            "feature_names": self.feature_names,
        }


class MultiClassifierTrainer:
    """Train multi-class classification model"""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None

    def create_multiclass_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create multi-class labels from operational state"""
        df = df.copy()
        
        state_mapping = {
            "CRITICALLY_LOW": 0,
            "LOW": 1,
            "BELOW_OPTIMAL": 2,
            "OPTIMAL": 3,
            "ABOVE_OPTIMAL": 4,
            "HIGH": 5,
            "CRITICALLY_HIGH": 6,
        }
        
        value = df["value"]
        df["operational_state"] = pd.cut(
            value,
            bins=[0, 10, 20, 30, 70, 80, 90, 100],
            labels=list(state_mapping.keys()),
        )
        df["state_label"] = df["operational_state"].map(state_mapping)
        
        return df

    def prepare_data(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        feature_cols = [
            col for col in df.columns
            if col not in [
                "timestamp",
                "sensor_id",
                "anomaly",
                "severity",
                "category",
                "operational_state",
                "state_label",
            ]
        ]
        self.feature_names = feature_cols
        
        X = df[feature_cols].values
        y = df["state_label"].values
        
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        
        return X_train, X_test, y_train, y_test

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train multi-class classifier"""
        logger.info("Training multi-class classifier...")
        
        df = self.create_multiclass_labels(df)
        X_train, X_test, y_train, y_test = self.prepare_data(df)
        
        self.model = GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=self.random_state,
        )
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision_weighted": float(precision_score(y_test, y_pred, average="weighted")),
            "recall_weighted": float(recall_score(y_test, y_pred, average="weighted")),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted")),
        }
        
        logger.info(f"Multi-class classifier metrics: {metrics}")
        
        return {
            "model": self.model,
            "scaler": self.scaler,
            "metrics": metrics,
            "feature_names": self.feature_names,
        }


class BatchProcessor:
    """Main batch processing pipeline"""

    def __init__(
        self,
        influx_url: str = "http://influxdb:8086",
        influx_token: str = "nt-scada-token-secret-key-12345",
        mlflow_uri: str = "http://mlflow:5000",
    ):
        self.data_loader = ScadaDataLoader(url=influx_url, token=influx_token)
        self.registry = ModelRegistry(registry_uri=mlflow_uri)
        self.report_dir = Path("/app/reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        """Execute complete batch processing pipeline"""
        logger.info("=" * 60)
        logger.info("NT-SCADA Batch Processing Pipeline")
        logger.info("=" * 60)

        try:
            if not self.data_loader.connect():
                raise RuntimeError("Failed to connect to InfluxDB")

            df = self.data_loader.load_sensor_data()
            if df.empty:
                raise ValueError("No sensor data loaded")

            df = FeatureEngineer.engineer_features(df)

            binary_result = self._train_binary_classifier(df)
            multiclass_result = self._train_multiclass_classifier(df)

            report = self._generate_report(binary_result, multiclass_result, len(df))
            self._save_report(report)

            logger.info("=" * 60)
            logger.info("Batch processing completed successfully")
            logger.info("=" * 60)

            return report

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
        finally:
            self.data_loader.close()

    def _train_binary_classifier(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train and register binary classifier"""
        trainer = BinaryClassifierTrainer()
        result = trainer.train(df)

        model_id = self.registry.register_model(
            model=result["model"],
            model_name="binary_classifier",
            model_type="RandomForest",
            version="v1.0",
            metrics=result["metrics"],
            params={
                "n_estimators": 200,
                "max_depth": 15,
                "min_samples_split": 5,
            },
            metadata={
                "description": "Binary anomaly detection classifier",
                "training_date": datetime.utcnow().isoformat(),
            },
            features=result["feature_names"],
        )

        result["model_id"] = model_id
        return result

    def _train_multiclass_classifier(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train and register multi-class classifier"""
        trainer = MultiClassifierTrainer()
        result = trainer.train(df)

        model_id = self.registry.register_model(
            model=result["model"],
            model_name="multiclass_classifier",
            model_type="GradientBoosting",
            version="v1.0",
            metrics=result["metrics"],
            params={
                "n_estimators": 150,
                "learning_rate": 0.1,
                "max_depth": 5,
            },
            metadata={
                "description": "Multi-class operational state classifier",
                "training_date": datetime.utcnow().isoformat(),
            },
            features=result["feature_names"],
        )

        result["model_id"] = model_id
        return result

    def _generate_report(
        self,
        binary_result: Dict,
        multiclass_result: Dict,
        total_samples: int,
    ) -> Dict[str, Any]:
        """Generate batch processing report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_samples": total_samples,
            "binary_classifier": {
                "model_id": binary_result["model_id"],
                "metrics": binary_result["metrics"],
            },
            "multiclass_classifier": {
                "model_id": multiclass_result["model_id"],
                "metrics": multiclass_result["metrics"],
            },
        }

    def _save_report(self, report: Dict[str, Any]) -> None:
        """Save report to file"""
        report_file = self.report_dir / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved: {report_file}")


from pathlib import Path


if __name__ == "__main__":
    processor = BatchProcessor()
    processor.run()
