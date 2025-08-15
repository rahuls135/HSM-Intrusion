"""
HSM Light-Only Training using Grid Search with K-Fold Cross Validation
Finds optimal threshold for light sensor only
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import os
from tqdm import tqdm

def evaluate_threshold(X, y, threshold):
    """
    Evaluate threshold-based classification for light sensor
    Anomaly if: light > threshold
    """
    predictions = (X > threshold).astype(int)
    return predictions

def grid_search_kfold(X, y, light_range, n_folds=5):
    """
    Perform grid search with k-fold cross validation for single sensor
    """
    # Initialize stratified k-fold
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    best_score = -np.inf
    best_params = {}
    all_results = []
    
    # Progress bar
    pbar = tqdm(total=len(light_range), desc="Grid Search Progress")
    
    for light_thresh in light_range:
        # Store scores for each fold
        fold_accuracies = []
        fold_precisions = []
        fold_recalls = []
        fold_f1s = []
        
        # Perform k-fold cross validation
        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Make predictions on validation set
            val_predictions = evaluate_threshold(X_val, y_val, light_thresh)
            
            # Calculate metrics
            fold_accuracies.append(accuracy_score(y_val, val_predictions))
            fold_precisions.append(precision_score(y_val, val_predictions, zero_division=0))
            fold_recalls.append(recall_score(y_val, val_predictions, zero_division=0))
            fold_f1s.append(f1_score(y_val, val_predictions, zero_division=0))
        
        # Calculate mean and std across folds
        mean_accuracy = np.mean(fold_accuracies)
        std_accuracy = np.std(fold_accuracies)
        mean_precision = np.mean(fold_precisions)
        mean_recall = np.mean(fold_recalls)
        mean_f1 = np.mean(fold_f1s)
        
        # Store results
        result = {
            'light_threshold': light_thresh,
            'mean_accuracy': mean_accuracy,
            'std_accuracy': std_accuracy,
            'mean_precision': mean_precision,
            'mean_recall': mean_recall,
            'mean_f1': mean_f1
        }
        all_results.append(result)
        
        # Update best parameters (using F1 score as primary metric)
        if mean_f1 > best_score:
            best_score = mean_f1
            best_params = result
        
        pbar.update(1)
    
    pbar.close()
    return best_params, all_results

# Load data
df = pd.read_csv('hsm_data.csv')

# Check columns
print(f"Columns found: {df.columns.tolist()}")

# Prepare features and labels (single feature now)
X = df[['light']]  # Keep as DataFrame for consistency
y = (df['label'] == 'anomaly').astype(int)

print(f"\nDataset statistics:")
print(f"Total samples: {len(df)}")
print(f"Normal samples: {(y==0).sum()} ({100*(y==0).sum()/len(df):.1f}%)")
print(f"Anomaly samples: {(y==1).sum()} ({100*(y==1).sum()/len(df):.1f}%)")

# Analyze data distribution
print(f"\nLight sensor data ranges:")
print(f"Overall: {X['light'].min():.4f} to {X['light'].max():.4f} V")

print(f"\nNormal class:")
normal_data = X[y==0]['light']
print(f"  Range: {normal_data.min():.4f} to {normal_data.max():.4f} V")
print(f"  Mean: {normal_data.mean():.4f} V")
print(f"  Std: {normal_data.std():.4f} V")

print(f"\nAnomaly class:")
anomaly_data = X[y==1]['light']
print(f"  Range: {anomaly_data.min():.4f} to {anomaly_data.max():.4f} V")
print(f"  Mean: {anomaly_data.mean():.4f} V")
print(f"  Std: {anomaly_data.std():.4f} V")

# Check for overlap
overlap_exists = normal_data.max() >= anomaly_data.min()
print(f"\nClass overlap: {'Yes' if overlap_exists else 'No'}")
if overlap_exists:
    print(f"  Overlap range: {anomaly_data.min():.4f} to {normal_data.max():.4f} V")

# Define search range for threshold
# Use percentiles and specific points
light_percentiles = np.percentile(X['light'], np.linspace(5, 95, 50))

# Add some specific values in the overlap region if it exists
if overlap_exists:
    overlap_points = np.linspace(anomaly_data.min(), normal_data.max(), 20)
    light_candidates = np.unique(np.concatenate([light_percentiles, overlap_points]))
else:
    light_candidates = light_percentiles

# Sort candidates
light_candidates = np.sort(light_candidates)

print(f"\nGrid search configuration:")
print(f"Light threshold candidates: {len(light_candidates)} values")
print(f"Range: {light_candidates.min():.4f} to {light_candidates.max():.4f}")
print(f"K-fold cross validation: 5 folds")

# Perform grid search with k-fold cross validation
print(f"\n{'='*60}")
print("Running Grid Search with 5-Fold Cross Validation...")
print(f"{'='*60}\n")

best_params, all_results = grid_search_kfold(X, y, light_candidates, n_folds=5)

print(f"\n{'='*60}")
print("OPTIMAL THRESHOLD FOUND")
print(f"{'='*60}")
print(f"Light threshold: {best_params['light_threshold']:.6f} V")
print(f"\nCross-validation metrics:")
print(f"Accuracy: {best_params['mean_accuracy']:.4f} ± {best_params['std_accuracy']:.4f}")
print(f"Precision: {best_params['mean_precision']:.4f}")
print(f"Recall: {best_params['mean_recall']:.4f}")
print(f"F1 Score: {best_params['mean_f1']:.4f}")

# Test on full dataset with optimal threshold
final_predictions = evaluate_threshold(X['light'], y, best_params['light_threshold'])

print(f"\nPerformance on full dataset:")
print(classification_report(y, final_predictions, 
                           target_names=['Normal', 'Anomaly'],
                           digits=4))

# Save results
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('mean_f1', ascending=False)
results_df.to_csv('light_threshold_results.csv', index=False)

# Export for Pico deployment
params_file = 'onboard/model_params.py'
with open(params_file, 'w') as f:
    f.write("# Optimal light threshold from Grid Search + K-Fold Cross Validation\n")
    f.write("# Trained on light sensor only (hsm_data3.csv)\n\n")
    f.write(f"# Threshold value (in Volts)\n")
    f.write(f"LIGHT_THRESHOLD = {best_params['light_threshold']:.6f}\n\n")
    f.write(f"# Model performance metrics (5-fold cross-validated)\n")
    f.write(f"CV_ACCURACY = {best_params['mean_accuracy']:.4f}\n")
    f.write(f"CV_STD = {best_params['std_accuracy']:.4f}\n")
    f.write(f"CV_F1_SCORE = {best_params['mean_f1']:.4f}\n")
    f.write(f"CV_PRECISION = {best_params['mean_precision']:.4f}\n")
    f.write(f"CV_RECALL = {best_params['mean_recall']:.4f}\n\n")
    f.write(f"# Detection logic for Pico:\n")
    f.write(f"# is_anomaly = (light > {best_params['light_threshold']:.6f})\n")

print(f"\nModel parameters saved to {params_file}")
print(f"Detailed results saved to light_threshold_results.csv")

# Show top 5 thresholds
print(f"\nTop 5 thresholds by F1 score:")
top_5 = results_df.head(5)
for idx, row in top_5.iterrows():
    print(f"  Threshold: {row['light_threshold']:.4f} V, "
          f"F1: {row['mean_f1']:.4f}, Acc: {row['mean_accuracy']:.4f}")

# Analyze the threshold position
print(f"\n{'='*60}")
print("THRESHOLD ANALYSIS")
print(f"{'='*60}")
optimal_thresh = best_params['light_threshold']
normal_below = (normal_data <= optimal_thresh).sum()
normal_above = (normal_data > optimal_thresh).sum()
anomaly_below = (anomaly_data <= optimal_thresh).sum()
anomaly_above = (anomaly_data > optimal_thresh).sum()

print(f"With threshold at {optimal_thresh:.6f} V:")
print(f"  Normal samples: {normal_below}/{len(normal_data)} below, {normal_above}/{len(normal_data)} above")
print(f"  Anomaly samples: {anomaly_below}/{len(anomaly_data)} below, {anomaly_above}/{len(anomaly_data)} above")
print(f"  False positives: {normal_above}/{len(normal_data)} ({100*normal_above/len(normal_data):.1f}%)")
print(f"  False negatives: {anomaly_below}/{len(anomaly_data)} ({100*anomaly_below/len(anomaly_data):.1f}%)")

print(f"\n{'='*60}")
print("Training Complete!")
print(f"{'='*60}")