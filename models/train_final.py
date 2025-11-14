"""
Final bulletproof training with perfect feature alignment
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import joblib
import json

print("="*80)
print("🎯 Final Model Training with Feature Alignment")
print("="*80)

# Load data
print("\n📂 Loading data...")
df = pd.read_excel(r'..\data\swat\Normal Data 2023\22June2020 (1).xlsx')
print(f"✅ Loaded: {df.shape}")
print(f"📋 Columns: {list(df.columns)[:5]}...")

# Get features - SORTED alphabetically for consistency
all_features = sorted([col for col in df.columns if col != 't_stamp'])
print(f"\n✅ Will use {len(all_features)} features")
print(f"📋 First 5: {all_features[:5]}")
print(f"📋 Last 5: {all_features[-5:]}")

# Extract and prepare data
X = df[all_features].copy()

# Convert to numeric
print("\n🔄 Converting to numeric...")
for col in X.columns:
    X[col] = pd.to_numeric(X[col], errors='coerce')

# Fill NaN
X = X.fillna(0)
X = X.replace([np.inf, -np.inf], 0)

print(f"✅ Data prepared: {X.shape}")
print(f"✅ All numeric: {X.select_dtypes(include=[np.number]).shape[1]} columns")

# Sample for training
if len(X) > 5000:
    X = X.sample(5000, random_state=42)
    print(f"📉 Sampled to {len(X)} rows")

# Labels
y_normal = np.zeros(len(X))

# Create synthetic attacks
print("\n🔄 Creating synthetic attack data...")
n_attacks = 1000
X_attack = X.sample(n_attacks, random_state=42).copy()

for col in X_attack.columns:
    if X_attack[col].std() > 0:
        mask = np.random.rand(len(X_attack)) < 0.3
        X_attack.loc[mask, col] *= np.random.uniform(2, 5, mask.sum())

y_attack = np.ones(len(X_attack))

# Combine
X_all = pd.concat([X, X_attack], ignore_index=True)
y_all = np.concatenate([y_normal, y_attack])

print(f"\n✅ Combined: {X_all.shape}")
print(f"📊 Features in training data: {list(X_all.columns)[:5]}...")

# Final check
print(f"\n🔍 Verifying feature count: {len(X_all.columns)} features")
print(f"🔍 Verifying all columns: {X_all.columns.tolist() == all_features}")

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_all, y_all, test_size=0.3, random_state=42, stratify=y_all
)

print(f"\n📊 Train: {X_train.shape}")
print(f"📊 Test: {X_test.shape}")

# Scale
print("\n⚖️  Scaling...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train
print("\n🤖 Training Random Forest...")
model = RandomForestClassifier(
    n_estimators=50,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

# Evaluate
accuracy = model.score(X_test_scaled, y_test)
print(f"✅ Training complete!")
print(f"📊 Accuracy: {accuracy:.3f}")

# Verify
print(f"\n🔍 Model expects: {model.n_features_in_} features")
print(f"🔍 Scaler expects: {scaler.n_features_in_} features")
print(f"🔍 Feature list has: {len(all_features)} features")

assert model.n_features_in_ == len(all_features), "Feature count mismatch!"

# Save everything
print("\n💾 Saving...")
joblib.dump(model, 'binary_classifier.pkl')
joblib.dump(scaler, 'scaler.pkl')

with open('feature_names.json', 'w') as f:
    json.dump(all_features, f, indent=2)

print(f"✅ Model saved: binary_classifier.pkl")
print(f"✅ Scaler saved: scaler.pkl")
print(f"✅ Features saved: feature_names.json ({len(all_features)} features)")

print("\n" + "="*80)
print("✅ SUCCESS! All components aligned")
print("="*80)