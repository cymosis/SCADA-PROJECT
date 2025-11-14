import pandas as pd
import json

# Load the Excel file
df = pd.read_excel(r'..\data\swat\Normal Data 2023\22June2020 (1).xlsx')

# Get all features except t_stamp, sorted alphabetically
features = sorted([col for col in df.columns if col != 't_stamp'])

print(f"Found {len(features)} features")
print(f"First 10: {features[:10]}")

# Save to JSON
with open('feature_names.json', 'w') as f:
    json.dump(features, f)

print("✅ Saved to feature_names.json")