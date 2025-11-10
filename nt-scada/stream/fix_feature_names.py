"""
Quick script to add feature names to the trained models
"""
import joblib
import numpy as np

# Load models
binary_model = joblib.load('../batch/models/binary_classifier_swat.pkl')
fine_grained_model = joblib.load('../batch/models/fine_grained_classifier_swat.pkl')

# Set feature names (use the same features we trained with)
feature_names = ['P1_STATE', 'LIT101.Pv', 'FIT101.Pv', 'MV101.Status']

# Update the models with feature names
binary_model.feature_names_in_ = np.array(feature_names)
fine_grained_model.feature_names_in_ = np.array(feature_names)

# Save updated models
joblib.dump(binary_model, '../batch/models/binary_classifier_swat.pkl')
joblib.dump(fine_grained_model, '../batch/models/fine_grained_classifier_swat.pkl')

print("✅ Feature names added to models")