# Optimal light threshold from Grid Search + K-Fold Cross Validation
# Trained on light sensor only (hsm_data3.csv)

# Threshold value (in Volts)
LIGHT_THRESHOLD = 0.495627

# Model performance metrics (5-fold cross-validated)
CV_ACCURACY = 0.9919
CV_STD = 0.0108
CV_F1_SCORE = 0.9930
CV_PRECISION = 0.9864
CV_RECALL = 1.0000

# Detection logic for Pico:
# is_anomaly = (light > 0.495627)
