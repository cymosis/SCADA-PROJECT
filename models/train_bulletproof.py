"""
Bulletproof training - keeps all features explicitly
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import joblib

print("="*80)
print("🎯 Bulletproof Training Script")
print("="*80)

# Load data
print("\n📂 Loading data...")
df = pd.read_excel(r'..\data\swat\Normal Data 2023\22June2020 (1).xlsx')
print(f"✅ Loaded shape: {df.shape}")
print(f"✅ Columns: {len(df.columns)}")

# Get all features EXCEPT t_stamp
all_columns = list(df.columns)
print(f"\n📋 All columns: {all_columns[:5]}...")

features = [col for col in all_columns if col != 't_stamp']
print(f"\n✅ Feature columns: {len(features)}")
print(f"📋 First 10 features: {features[:10]}")

# Extract features
X = df[features].copy()
print(f"\n✅ X shape before conversion: {X.shape}")

# Convert EACH column to numeric individually
print("\n🔄 Converting to numeric...")
for i, col in enumerate(features):
    X[col] = pd.to_numeric(X[col], errors='coerce')
    if i % 10 == 0:
        print(f"  Converted {i}/{len(features)} columns...")

print(f"✅ Conversion complete")

# Fill NaN with 0
print("\n🔄 Filling NaN values...")
X = X.fillna(0)
print(f"✅ X shape after fillna: {X.shape}")

# Replace inf values
X = X.replace([np.inf, -np.inf], 0)
print(f"✅ Final X shape: {X.shape}")

# Sample if too large
if len(X) > 5000:
    X = X.sample(n=5000, random_state=42)
    print(f"📉 Sampled to {len(X)} rows")

# Create labels (all normal)
y_normal = np.zeros(len(X))

# Create synthetic attack data
print("\n🔄 Creating attack data...")
n_attacks = min(1000, len(X) // 2)
X_attack = X.sample(n=n_attacks, random_state=42).copy()

# Add anomalies
for col in X_attack.columns:
    if X_attack[col].std() > 0:
        mask = np.random.rand(len(X_attack)) < 0.3
        X_attack.loc[mask, col] *= np.random.uniform(2, 5, mask.sum())

y_attack = np.ones(len(X_attack))

# Combine
print("\n📊 Combining datasets...")
X_combined = pd.concat([X, X_attack], ignore_index=True)
y_combined = np.concatenate([y_normal, y_attack])

print(f"✅ Combined shape: {X_combined.shape}")
print(f"✅ Features in combined data: {X_combined.shape[1]}")
print(f"📊 Normal: {sum(y_combined==0)}, Attack: {sum(y_combined==1)}")

# Verify no NaN or inf
X_combined = X_combined.replace([np.inf, -np.inf], 0)
X_combined = X_combined.fillna(0)

# Split
print("\n📊 Splitting...")
X_train, X_test, y_train, y_test = train_test_split(
    X_combined, y_combined, test_size=0.3, random_state=42
)

print(f"✅ Train shape: {X_train.shape}")
print(f"✅ Test shape: {X_test.shape}")

# Scale
print("\n⚖️  Scaling...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"✅ Scaled train shape: {X_train_scaled.shape}")

# Train
print("\n🤖 Training RandomForest...")
model = RandomForestClassifier(
    n_estimators=50,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

print("✅ Training complete!")

# Test
accuracy = model.score(X_test_scaled, y_test)
print(f"\n📊 Test Accuracy: {accuracy:.3f}")

# Verify feature count
print(f"\n🔍 Model n_features_in_: {model.n_features_in_}")
print(f"🔍 Scaler n_features_in_: {scaler.n_features_in_}")

# Save
print("\n💾 Saving...")
joblib.dump(model, 'binary_classifier.pkl')
joblib.dump(scaler, 'scaler.pkl')

print(f"✅ Model saved: binary_classifier.pkl")
print(f"✅ Scaler saved: scaler.pkl")

print("\n" + "="*80)
print(f"✅ SUCCESS! Model trained with {model.n_features_in_} features")
print("="*80)