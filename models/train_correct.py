"""
Correct Binary Classification Training
Uses exact features from streaming data
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib

print("=" * 80)
print("🎯 NT-SCADA Binary Classification - Correct Training")
print("=" * 80)

# Load normal data
NORMAL_PATH = r'..\data\swat\Normal Data 2023\22June2020 (1).xlsx'

print("\n📂 Loading normal dataset...")
normal_df = pd.read_excel(NORMAL_PATH)
print(f"✅ Shape: {normal_df.shape}")
print(f"📋 Columns: {list(normal_df.columns)[:5]}...")

# Define features (all except timestamp)
feature_columns = [col for col in normal_df.columns if col != 't_stamp']
print(f"\n✅ Training with {len(feature_columns)} features")

# Prepare normal data
X_normal = normal_df[feature_columns].copy()

# Convert all to numeric
print("\n🔄 Converting to numeric...")
for col in X_normal.columns:
    X_normal[col] = pd.to_numeric(X_normal[col], errors='coerce')

# Fill NaN
X_normal = X_normal.fillna(X_normal.mean(numeric_only=True))
X_normal = X_normal.fillna(0)

# Sample for faster training
if len(X_normal) > 5000:
    X_normal = X_normal.sample(n=5000, random_state=42)
    print(f"📉 Sampled to {len(X_normal)} rows")

y_normal = np.zeros(len(X_normal))

# Create synthetic attack data
print("\n🔄 Creating synthetic attack data...")
X_attack = X_normal.sample(n=min(1000, len(X_normal)), random_state=42).copy()

# Inject anomalies
for col in X_attack.columns:
    if X_attack[col].std() > 0:
        # 30% get spikes
        spike_idx = np.random.choice(len(X_attack), size=int(len(X_attack)*0.3), replace=False)
        X_attack.iloc[spike_idx, X_attack.columns.get_loc(col)] *= np.random.uniform(2, 5, len(spike_idx))
        
        # 20% get drops
        drop_idx = np.random.choice(len(X_attack), size=int(len(X_attack)*0.2), replace=False)
        X_attack.iloc[drop_idx, X_attack.columns.get_loc(col)] *= np.random.uniform(0.1, 0.5, len(drop_idx))

y_attack = np.ones(len(X_attack))

# Combine
print("\n📊 Combining datasets...")
X = pd.concat([X_normal, X_attack], ignore_index=True)
y = np.concatenate([y_normal, y_attack])

print(f"✅ Total: {len(X)} samples")
print(f"✅ Features: {X.shape[1]}")
print(f"📊 Normal: {sum(y==0)}, Attack: {sum(y==1)}")

# Check for any remaining NaN or inf
X = X.replace([np.inf, -np.inf], 0)
X = X.fillna(0)

# Split
print("\n📊 Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# Scale
print("\n⚖️  Scaling...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train
print("\n🤖 Training Random Forest...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)
print("✅ Training complete!")

# Evaluate
print("\n📊 Evaluating...")
y_pred = model.predict(X_test_scaled)
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

print("\n📈 Classification Report:")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Attack']))

print("\n📊 Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(cm)

roc = roc_auc_score(y_test, y_pred_proba)
print(f"\n🎯 ROC-AUC: {roc:.4f}")

# Feature importance
importance_df = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n🔝 Top 10 Features:")
print(importance_df.head(10))

# Save everything
print("\n💾 Saving model...")
joblib.dump(model, 'binary_classifier.pkl')
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(feature_columns, 'feature_columns.pkl')

print(f"✅ Saved: binary_classifier.pkl")
print(f"✅ Saved: scaler.pkl")  
print(f"✅ Saved: feature_columns.pkl")
print(f"✅ Model expects {len(feature_columns)} features")

print("\n" + "="*80)
print("✅ SUCCESS! Model ready for deployment")
print("="*80)