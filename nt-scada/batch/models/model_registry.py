"""
NT-SCADA Model Registry
Manages model versioning, registration, and retrieval using MLflow
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import mlflow
from mlflow.models import ModelSignature
from mlflow.types.schema import Schema, ColSpec
import joblib
import numpy as np


logger = logging.getLogger(__name__)


class ModelRegistry:
    """Professional model registry for NT-SCADA"""

    def __init__(
        self,
        registry_uri: str = "http://mlflow:5000",
        artifact_path: str = "/app/models/registry",
        experiment_name: str = "nt-scada-models"
    ):
        """
        Initialize model registry.
        
        Args:
            registry_uri: MLflow tracking server URI
            artifact_path: Local artifact storage path
            experiment_name: MLflow experiment name
        """
        self.registry_uri = registry_uri
        self.artifact_path = artifact_path
        self.experiment_name = experiment_name
        
        Path(self.artifact_path).mkdir(parents=True, exist_ok=True)
        
        try:
            mlflow.set_tracking_uri(self.registry_uri)
            mlflow.set_experiment(self.experiment_name)
            logger.info(f"Connected to MLflow at {registry_uri}")
        except Exception as e:
            logger.warning(f"MLflow not available: {e}. Using local registry.")
            self.use_local_registry = True
        else:
            self.use_local_registry = False

    def register_model(
        self,
        model: Any,
        model_name: str,
        model_type: str,
        version: str,
        metrics: Dict[str, float],
        params: Dict[str, Any],
        metadata: Dict[str, Any],
        features: list,
    ) -> str:
        """
        Register model with metadata.
        
        Args:
            model: Trained model object
            model_name: Name of the model (e.g., 'binary_classifier')
            model_type: Type of model (e.g., 'RandomForest', 'GradientBoosting')
            version: Version string (e.g., 'v1.0')
            metrics: Dictionary of evaluation metrics
            params: Dictionary of model hyperparameters
            metadata: Additional metadata
            features: List of feature names used
            
        Returns:
            Model ID for future reference
        """
        model_id = f"{model_name}_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.use_local_registry:
            return self._register_local(
                model, model_id, model_type, metrics, params, metadata, features
            )
        else:
            return self._register_mlflow(
                model, model_id, model_name, model_type, metrics, params, metadata, features
            )

    def _register_local(
        self,
        model: Any,
        model_id: str,
        model_type: str,
        metrics: Dict[str, float],
        params: Dict[str, Any],
        metadata: Dict[str, Any],
        features: list,
    ) -> str:
        """Register model locally"""
        model_dir = Path(self.artifact_path) / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / "model.pkl"
        joblib.dump(model, str(model_file))
        
        manifest = {
            "model_id": model_id,
            "model_type": model_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "params": params,
            "metadata": metadata,
            "features": features,
        }
        
        with open(model_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Model registered locally: {model_id}")
        return model_id

    def _register_mlflow(
        self,
        model: Any,
        model_id: str,
        model_name: str,
        model_type: str,
        metrics: Dict[str, float],
        params: Dict[str, Any],
        metadata: Dict[str, Any],
        features: list,
    ) -> str:
        """Register model with MLflow"""
        with mlflow.start_run(run_name=model_id):
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            
            mlflow.log_dict(metadata, "metadata.json")
            mlflow.log_dict({"features": features}, "features.json")
            
            signature = self._create_signature(len(features))
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                signature=signature,
                registered_model_name=model_name,
            )
            
            logger.info(f"Model registered with MLflow: {model_id}")
            return model_id

    def load_model(self, model_id: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Load model and its metadata.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Tuple of (model, metadata)
        """
        if self.use_local_registry:
            return self._load_local(model_id)
        else:
            return self._load_mlflow(model_id)

    def _load_local(self, model_id: str) -> Tuple[Any, Dict[str, Any]]:
        """Load model from local registry"""
        model_dir = Path(self.artifact_path) / model_id
        
        if not model_dir.exists():
            raise FileNotFoundError(f"Model not found: {model_id}")
        
        model = joblib.load(str(model_dir / "model.pkl"))
        
        with open(model_dir / "manifest.json", "r") as f:
            metadata = json.load(f)
        
        logger.info(f"Model loaded from local registry: {model_id}")
        return model, metadata

    def _load_mlflow(self, model_id: str) -> Tuple[Any, Dict[str, Any]]:
        """Load model from MLflow"""
        try:
            model = mlflow.sklearn.load_model(f"models:/{model_id}/latest")
            logger.info(f"Model loaded from MLflow: {model_id}")
            return model, {}
        except Exception as e:
            logger.error(f"Failed to load model from MLflow: {e}")
            raise

    def list_models(self) -> list:
        """List all registered models"""
        if self.use_local_registry:
            models = list(Path(self.artifact_path).glob("**/model.pkl"))
            return [str(m.parent.name) for m in models]
        else:
            try:
                registered_models = mlflow.search_registered_models()
                return [model.name for model in registered_models]
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                return []

    def get_model_metadata(self, model_id: str) -> Dict[str, Any]:
        """Get model metadata without loading the model"""
        if self.use_local_registry:
            model_dir = Path(self.artifact_path) / model_id
            if not (model_dir / "manifest.json").exists():
                raise FileNotFoundError(f"Model not found: {model_id}")
            
            with open(model_dir / "manifest.json", "r") as f:
                return json.load(f)
        else:
            try:
                run = mlflow.search_runs(
                    experiment_names=[self.experiment_name],
                    filter_string=f"tags.mlflow.runName = '{model_id}'"
                )
                if not run.empty:
                    return run.iloc[0].to_dict()
                raise FileNotFoundError(f"Model not found: {model_id}")
            except Exception as e:
                logger.error(f"Failed to get metadata: {e}")
                raise

    @staticmethod
    def _create_signature(n_features: int) -> ModelSignature:
        """Create MLflow model signature"""
        input_schema = Schema([
            ColSpec(name=f"feature_{i}", type="double")
            for i in range(n_features)
        ])
        output_schema = Schema([ColSpec(name="prediction", type="double")])
        return ModelSignature(inputs=input_schema, outputs=output_schema)


class ModelVersionManager:
    """Manages model versions and switching"""

    def __init__(self, registry: ModelRegistry):
        """Initialize version manager"""
        self.registry = registry
        self.active_models: Dict[str, str] = {}

    def activate_model(self, model_name: str, model_id: str) -> None:
        """Activate a specific model version"""
        model, metadata = self.registry.load_model(model_id)
        self.active_models[model_name] = model_id
        logger.info(f"Activated {model_name}: {model_id}")

    def get_active_model(self, model_name: str) -> Tuple[Any, str]:
        """Get currently active model"""
        if model_name not in self.active_models:
            raise ValueError(f"No active model for {model_name}")
        
        model_id = self.active_models[model_name]
        model, _ = self.registry.load_model(model_id)
        return model, model_id

    def list_active_models(self) -> Dict[str, str]:
        """List all active models"""
        return self.active_models.copy()
