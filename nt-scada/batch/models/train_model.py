"""
NT-SCADA Batch Analytics and Model Training (Debug Version)
Performs batch time-series analytics on historical data
Trains binary and multi-class classification models
Generates daily statistics and reports
"""

import os
import pickle
import json
import joblib
from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
import warnings

warnings.filterwarnings('ignore')

# -----------------------------
# InfluxDB configuration
# -----------------------------
INFLUXDB_URL = "http://localhost:8086"  # or your Docker container URL
INFLUXDB_TOKEN = "mytoken"
INFLUXDB_ORG = "scada"
INFLUXDB_BUCKET = "normal_data"
ATTACK_BUCKET = "attack_data"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Models and reports folders
MODEL_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# Paths for files
MODEL_OUTPUT_PATH = os.path.join(MODEL_DIR, "binary_classifier.pkl")
SCALER_OUTPUT_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
REPORT_OUTPUT_PATH = os.path.join(REPORT_DIR, "binary_classification_report.txt")

# Make sure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# -----------------------------
# Connect to InfluxDB
# -----------------------------
client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

health = client.health()
print("InfluxDB health:", health.status)

# -----------------------------
# Simple query: last 10 records
# -----------------------------
query_api = client.query_api()
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: 60)             // last 1 day
  |> filter(fn: (r) => r._measurement == "actuator_data")
  |> limit(n:10)
  |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
    )
|> drop(columns: ["_start","_stop","result","table","_measurement"])

'''

result = query_api.query(query=query)

# Convert to DataFrame
records = []
for table in result:
    for record in table.records:
        records.append(record.values)

normal_df = pd.DataFrame(records)
print("Query result:")
print(normal_df.shape)
#================================================
# Simple query: last 10 records
# -----------------------------

query1 = f'''
from(bucket: "{ATTACK_BUCKET}")
  |> range(start: time(v: 0))           // last 1 day
  |> filter(fn: (r) => r._measurement == "actuator_data")
  |> limit(n:10)
  |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
    )
|> drop(columns: ["_start","_stop","result","table","_measurement"])

'''

result1 = query_api.query(query=query1)

# Convert to DataFrame
records1 = []
for table in result1:
    for record in table.records:
        records1.append(record.values)

attack_df = pd.DataFrame(records1)
print("Attack Query result:")
print(attack_df.shape)

#=================================================================================
def load_and_prepare_data():
    normal_df['Attack'] = 0
    attack_df['Attack'] = 1
    df = pd.concat([normal_df, attack_df], ignore_index=True)
    print(f" Combined dataset: {df.shape}")
        
    # Remove timestamp and non-numeric columns
    exclude_cols = ['Timestamp', 't_stamp', 'Date', 'Time', 'label', 'Attack']
        
    # Get common features between both datasets
    normal_features = set([col for col in normal_df.columns if col not in exclude_cols])
    attack_features = set([col for col in attack_df.columns if col not in exclude_cols])
        
    # Use only common features that exist in both datasets
    feature_columns = sorted(list(normal_features.intersection(attack_features)))
        
    print(f"Common features found: {len(feature_columns)}")
    print(f"Feature names: {feature_columns[:10]}...")
    X = df[feature_columns]
    y = df['Attack']
        
    # Convert to numeric
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
        
    X = X.fillna(X.mean(numeric_only=True))
        
    print(f"Features: {X.shape[1]}")
    print(f"Samples: {X.shape[0]}")
    print(f"Class distribution: {y.value_counts().to_dict()}")
        
    return X, y, feature_columns

def load_and_prepare_multiclass_data():
    """Load and prepare data for multi-class classification (Normal vs Attack Types)."""
    # Add attack type information if available
    normal_df['Attack_Type'] = 'Normal'
    
    # Try to extract attack type from attack data
    if 'attack_type' in attack_df.columns:
        attack_df['Attack_Type'] = attack_df['attack_type']
    elif 'attack_label' in attack_df.columns:
        # Map attack labels to types
        attack_type_mapping = {
            1: 'Response_Injection',
            2: 'Command_Injection', 
            3: 'Sensor_Spoofing',
            4: 'Actuator_Manipulation',
            5: 'Communication_Attack'
        }
        attack_df['Attack_Type'] = attack_df['attack_label'].map(attack_type_mapping).fillna('Unknown_Attack')
    else:
        attack_df['Attack_Type'] = 'Unknown_Attack'
    
    df = pd.concat([normal_df, attack_df], ignore_index=True)
    print(f" Multi-class dataset: {df.shape}")
    
    # Remove timestamp and non-numeric columns
    exclude_cols = ['Timestamp', 't_stamp', 'Date', 'Time', 'label', 'Attack', 'attack_type', 'attack_label', 'Attack_Type']
    
    # Get common features
    normal_features = set([col for col in normal_df.columns if col not in exclude_cols])
    attack_features = set([col for col in attack_df.columns if col not in exclude_cols])
    feature_columns = sorted(list(normal_features.intersection(attack_features)))
    
    print(f"Common features found: {len(feature_columns)}")
    X = df[feature_columns]
    y = df['Attack_Type']
    
    # Convert to numeric
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.fillna(X.mean(numeric_only=True))
    
    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    print(f"Features: {X.shape[1]}")
    print(f"Samples: {X.shape[0]}")
    print(f"Attack type distribution: {y.value_counts().to_dict()}")
    print(f"Attack types: {list(label_encoder.classes_)}")
    
    return X, y_encoded, feature_columns, label_encoder

def create_feature_anomaly_labels(df, features, threshold=3.0):
    """Create fine-grained anomaly labels for each feature using statistical methods."""
    from scipy import stats
    
    anomaly_labels = {}
    
    for feature in features:
        if feature in df.columns and pd.api.types.is_numeric_dtype(df[feature]):
            # Calculate Z-scores for the feature
            z_scores = np.abs(stats.zscore(df[feature].dropna()))
            
            # Mark as anomalous if Z-score > threshold
            anomaly_mask = z_scores > threshold
            
            # Create binary labels: 0=normal, 1=anomalous
            anomaly_labels[feature] = (anomaly_mask.astype(int)).tolist()
    
    return anomaly_labels

def load_and_prepare_feature_anomaly_data(threshold=3.0):
    """Load and prepare data for fine-grained feature anomaly detection."""
    
    # Combine datasets
    normal_df['Attack'] = 0
    attack_df['Attack'] = 1
    df = pd.concat([normal_df, attack_df], ignore_index=True)
    print(f" Feature anomaly dataset: {df.shape}")
    
    # Remove timestamp and non-numeric columns
    exclude_cols = ['Timestamp', 't_stamp', 'Date', 'Time', 'label', 'Attack', 'attack_type', 'attack_label']
    
    # Get common features
    normal_features = set([col for col in normal_df.columns if col not in exclude_cols])
    attack_features = set([col for col in attack_df.columns if col not in exclude_cols])
    feature_columns = sorted(list(normal_features.intersection(attack_features)))
    
    print(f"Features for anomaly detection: {len(feature_columns)}")
    
    # Create feature anomaly labels
    anomaly_labels = create_feature_anomaly_labels(df, feature_columns, threshold)
    
    # Prepare data for each feature
    feature_datasets = {}
    
    for feature in feature_columns:
        if feature in anomaly_labels:
            X_feature = df[[feature]].copy()
            
            # Convert to numeric and handle missing values
            X_feature[feature] = pd.to_numeric(X_feature[feature], errors='coerce')
            X_feature = X_feature.fillna(X_feature.mean())
            
            y_feature = anomaly_labels[feature]
            
            # Only keep features with enough anomalies
            anomaly_rate = sum(y_feature) / len(y_feature)
            if anomaly_rate > 0.01 and anomaly_rate < 0.5:  # Between 1% and 50% anomalies
                feature_datasets[feature] = {
                    'X': X_feature,
                    'y': y_feature,
                    'anomaly_rate': anomaly_rate
                }
    
    print(f"Features with sufficient anomalies: {len(feature_datasets)}")
    
    return feature_datasets, feature_columns

def train_feature_anomaly_models(feature_datasets):
    """Train anomaly detection models for each feature."""
    
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    
    feature_models = {}
    feature_reports = {}
    
    print("\n Training Feature-Level Anomaly Detection Models...")
    
    for feature_name, data in feature_datasets.items():
        print(f"\n  Training model for {feature_name}...")
        
        X = data['X']
        y = data['y']
        anomaly_rate = data['anomaly_rate']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train multiple models
        models = {}
        
        # Random Forest for supervised anomaly detection
        rf_model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
            class_weight='balanced'
        )
        rf_model.fit(X_train_scaled, y_train)
        models['random_forest'] = rf_model
        
        # Isolation Forest for unsupervised anomaly detection
        iso_model = IsolationForest(
            contamination=anomaly_rate,
            random_state=42
        )
        iso_model.fit(X_train_scaled)
        models['isolation_forest'] = iso_model
        
        # Evaluate models
        model_reports = {}
        
        for model_name, model in models.items():
            if model_name == 'isolation_forest':
                # Isolation Forest returns -1 for anomalies, 1 for normal
                y_pred = model.predict(X_test_scaled)
                y_pred = [1 if pred == -1 else 0 for pred in y_pred]  # Convert to binary
            else:
                y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
            
            model_reports[model_name] = {
                'accuracy': accuracy,
                'report': report,
                'predictions': y_pred
            }
        
        # Store results
        feature_models[feature_name] = {
            'models': models,
            'scaler': scaler,
            'data': data
        }
        
        feature_reports[feature_name] = model_reports
        
        print(f"    Random Forest Accuracy: {model_reports['random_forest']['accuracy']:.4f}")
        print(f"    Isolation Forest Accuracy: {model_reports['isolation_forest']['accuracy']:.4f}")
        print(f"    Anomaly Rate: {anomaly_rate:.4f}")
    
    return feature_models, feature_reports

def save_feature_anomaly_models(feature_models, feature_reports):
    """Save feature-level anomaly detection models and reports."""
    
    # Create directories
    feature_model_dir = os.path.join(MODEL_DIR, "feature_anomaly_models")
    feature_report_dir = os.path.join(REPORT_DIR, "feature_anomaly_reports")
    os.makedirs(feature_model_dir, exist_ok=True)
    os.makedirs(feature_report_dir, exist_ok=True)
    
    print("\n Saving Feature Anomaly Models...")
    
    # Save each feature model
    for feature_name, model_data in feature_models.items():
        # Save models
        for model_name, model in model_data['models'].items():
            model_path = os.path.join(feature_model_dir, f"{feature_name}_{model_name}.pkl")
            joblib.dump(model, model_path)
        
        # Save scaler
        scaler_path = os.path.join(feature_model_dir, f"{feature_name}_scaler.pkl")
        joblib.dump(model_data['scaler'], scaler_path)
        
        print(f"    {feature_name}: Models saved")
    
    # Save comprehensive report
    report_path = os.path.join(feature_report_dir, "feature_anomaly_summary.txt")
    with open(report_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NT-SCADA Feature-Level Anomaly Detection - Training Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Features Analyzed: {len(feature_models)}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("Feature Performance Summary:\n")
        f.write("=" * 80 + "\n")
        
        for feature_name, reports in feature_reports.items():
            f.write(f"\n{feature_name}:\n")
            f.write(f"  Anomaly Rate: {feature_models[feature_name]['data']['anomaly_rate']:.4f}\n")
            
            for model_name, report in reports.items():
                f.write(f"  {model_name.replace('_', ' ').title()} Accuracy: {report['accuracy']:.4f}\n")
                f.write(f"  {model_name.replace('_', ' ').title()} F1-Score: {report['report']['weighted avg']['f1-score']:.4f}\n")
    
    print(f"\n Feature anomaly summary report saved to: {report_path}")
    
    return feature_model_dir, feature_report_dir

def train_model(X_train, y_train):
    """Train the binary classification model."""
    
    print("\n Training Random Forest Classifier...")
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'  # Handle class imbalance
    )
    
    model.fit(X_train, y_train)
    
    print("Model trained successfully")
    
    return model


def evaluate_model(model, X_test, y_test, feature_names):
    """Evaluate the model and generate reports."""
    
    print("\n Evaluating model...")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    print("\n Classification Report:")
    report = classification_report(y_test, y_pred, target_names=['Normal', 'Attack'])
    print(report)
    
    print("\n Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # ROC-AUC Score
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n ROC-AUC Score: {roc_auc:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n Top 10 Important Features:")
    print(feature_importance.head(10))
    
    return report, cm, roc_auc, feature_importance


def save_model_and_report(model, scaler, report, cm, roc_auc, feature_importance):
    """Save the trained model and evaluation reports."""
    
    # Create models directory if it doesn't exist
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    
    # Save model
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\n Model saved to: {MODEL_OUTPUT_PATH}")
    
    # Save scaler
    joblib.dump(scaler, SCALER_OUTPUT_PATH)
    print(f"Scaler saved to: {SCALER_OUTPUT_PATH}")
    
    # Save report
    with open(REPORT_OUTPUT_PATH, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NT-SCADA Binary Classification Model - Training Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model Type: Random Forest Classifier\n")
        f.write(f"ROC-AUC Score: {roc_auc:.4f}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("Classification Report:\n")
        f.write("=" * 80 + "\n")
        f.write(report)
        f.write("\n" + "=" * 80 + "\n")
        f.write("Confusion Matrix:\n")
        f.write("=" * 80 + "\n")
        f.write(str(cm))
        f.write("\n" + "=" * 80 + "\n")
        f.write("Feature Importance (Top 20):\n")
        f.write("=" * 80 + "\n")
        f.write(feature_importance.head(20).to_string())
        f.write("\n")
    
    print(f" Report saved to: {REPORT_OUTPUT_PATH}")


def main():
    """Main function to train all classification models with fine-grained anomaly detection."""
    
    print("=" * 80)
    print(" NT-SCADA Fine-Grained Anomaly Detection Model Training")
    print("=" * 80)
    
    # 1. Binary Classification (Normal vs Attack)
    print("\n" + "=" * 60)
    print("1. BINARY CLASSIFICATION (Normal vs Attack)")
    print("=" * 60)
    
    X_binary, y_binary, feature_names_binary = load_and_prepare_data()
    
    X_train_bin, X_test_bin, y_train_bin, y_test_bin = train_test_split(
        X_binary, y_binary, test_size=0.3, random_state=42, stratify=y_binary
    )
    
    scaler_bin = StandardScaler()
    X_train_bin_scaled = scaler_bin.fit_transform(X_train_bin)
    X_test_bin_scaled = scaler_bin.transform(X_test_bin)
    
    binary_model = train_model(X_train_bin_scaled, y_train_bin)
    
    bin_report, bin_cm, bin_roc_auc, bin_feature_importance = evaluate_model(
        binary_model, X_test_bin_scaled, y_test_bin, feature_names_binary
    )
    
    save_model_and_report(binary_model, scaler_bin, bin_report, bin_cm, bin_roc_auc, bin_feature_importance)
    
    # 2. Multi-Class Classification (Normal vs Attack Types)
    print("\n" + "=" * 60)
    print("2. MULTI-CLASS CLASSIFICATION (Normal vs Attack Types)")
    print("=" * 60)
    
    try:
        X_multi, y_multi, feature_names_multi, label_encoder_multi = load_and_prepare_multiclass_data()
        
        X_train_multi, X_test_multi, y_train_multi, y_test_multi = train_test_split(
            X_multi, y_multi, test_size=0.3, random_state=42, stratify=y_multi
        )
        
        scaler_multi = StandardScaler()
        X_train_multi_scaled = scaler_multi.fit_transform(X_train_multi)
        X_test_multi_scaled = scaler_multi.transform(X_test_multi)
        
        multiclass_model = train_model(X_train_multi_scaled, y_train_multi)
        
        multi_report, multi_cm, multi_roc_auc, multi_feature_importance = evaluate_model(
            multiclass_model, X_test_multi_scaled, y_test_multi, feature_names_multi
        )
        
        # Save multi-class model and encoder
        multiclass_model_path = os.path.join(MODEL_DIR, "multiclass_classifier.pkl")
        label_encoder_path = os.path.join(MODEL_DIR, "label_encoder.pkl")
        multiclass_report_path = os.path.join(REPORT_DIR, "multiclass_classification_report.txt")
        
        joblib.dump(multiclass_model, multiclass_model_path)
        joblib.dump(label_encoder_multi, label_encoder_path)
        
        print(f"\n Multi-class model saved to: {multiclass_model_path}")
        print(f"Label encoder saved to: {label_encoder_path}")
        
        with open(multiclass_report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("NT-SCADA Multi-Class Classification Model - Training Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model Type: Random Forest Classifier\n")
            f.write(f"Classes: {list(label_encoder_multi.classes_)}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("Classification Report:\n")
            f.write("=" * 80 + "\n")
            f.write(multi_report)
            f.write("\n" + "=" * 80 + "\n")
            f.write("Confusion Matrix:\n")
            f.write("=" * 80 + "\n")
            f.write(str(multi_cm))
            f.write("\n")
        
        print(f" Multi-class report saved to: {multiclass_report_path}")
        
    except Exception as e:
        print(f"\n⚠️  Multi-class classification failed: {e}")
        print("   This might be due to missing attack type information in the dataset.")
    
    # 3. Fine-Grained Feature Anomaly Detection
    print("\n" + "=" * 60)
    print("3. FINE-GRAINED FEATURE ANOMALY DETECTION")
    print("=" * 60)
    
    try:
        feature_datasets, feature_columns = load_and_prepare_feature_anomaly_data(threshold=2.5)
        
        if len(feature_datasets) > 0:
            feature_models, feature_reports = train_feature_anomaly_models(feature_datasets)
            feature_model_dir, feature_report_dir = save_feature_anomaly_models(feature_models, feature_reports)
            
            print(f"\n Feature Anomaly Detection Summary:")
            print(f"   • Total features analyzed: {len(feature_columns)}")
            print(f"   • Features with anomaly models: {len(feature_datasets)}")
            print(f"   • Models saved to: {feature_model_dir}")
            print(f"   • Reports saved to: {feature_report_dir}")
            
            # Show top 5 features with highest anomaly rates
            sorted_features = sorted(
                feature_datasets.items(), 
                key=lambda x: x[1]['anomaly_rate'], 
                reverse=True
            )[:5]
            
            print(f"\n Top 5 Features by Anomaly Rate:")
            for feature, data in sorted_features:
                print(f"   • {feature}: {data['anomaly_rate']:.4f} ({data['anomaly_rate']*100:.2f}% anomalies)")
        else:
            print("\n No features with sufficient anomalies found for fine-grained detection.")
            print("   Try adjusting the anomaly threshold or check data quality.")
            
    except Exception as e:
        print(f"\n Feature anomaly detection failed: {e}")
        print("   This might be due to insufficient data or statistical issues.")
    
    # Summary
    print("\n" + "=" * 80)
    print("FINE-GRAINED ANOMALY DETECTION TRAINING COMPLETED!")
    print("=" * 80)
    print("\n Models Saved:")
    print(f"   • Binary Classifier: {MODEL_OUTPUT_PATH}")
    print(f"   • Scaler: {SCALER_OUTPUT_PATH}")
    
    multiclass_model_path = os.path.join(MODEL_DIR, "multiclass_classifier.pkl")
    if os.path.exists(multiclass_model_path):
        print(f"   • Multi-class Classifier: {multiclass_model_path}")
        label_encoder_path = os.path.join(MODEL_DIR, "label_encoder.pkl")
        if os.path.exists(label_encoder_path):
            print(f"   • Label Encoder: {label_encoder_path}")
    
    feature_model_dir = os.path.join(MODEL_DIR, "feature_anomaly_models")
    if os.path.exists(feature_model_dir):
        print(f"   • Feature Anomaly Models: {feature_model_dir}")
    
    print("\n Reports Generated:")
    print(f"   • Binary Classification: {REPORT_OUTPUT_PATH}")
    
    multiclass_report_path = os.path.join(REPORT_DIR, "multiclass_classification_report.txt")
    if os.path.exists(multiclass_report_path):
        print(f"   • Multi-class Classification: {multiclass_report_path}")
    
    feature_report_dir = os.path.join(REPORT_DIR, "feature_anomaly_reports")
    if os.path.exists(feature_report_dir):
        feature_summary_path = os.path.join(feature_report_dir, "feature_anomaly_summary.txt")
        if os.path.exists(feature_summary_path):
            print(f"   • Feature Anomaly Summary: {feature_summary_path}")
    
    print("\n Classification Levels:")
    print("   • Level 1: Normal vs Attack (Binary)")
    print("   • Level 2: Normal vs Attack Types (Multi-class)")
    print("   • Level 3: Feature-Level Anomaly Detection (Fine-grained)")
    print("   • Level 4: Per-Sensor Anomaly Classification (Advanced)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
