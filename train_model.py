"""
Train ML model for AI voice detection.
Uses synthetic data and RandomForest classifier.
"""
import numpy as np
import os
import sys
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

def generate_training_data(n_samples_per_class=500):
    """
    Generate synthetic training data.
    Class 0 = HUMAN, Class 1 = AI_GENERATED
    """
    np.random.seed(42)
    
    # HUMAN voice features (more variation, higher f0_var, higher ZCR)
    human_data = []
    for _ in range(n_samples_per_class):
        duration = np.random.uniform(0.5, 30.0)
        f0_var = np.random.uniform(100, 2000)  # High pitch variance
        zcr_mean = np.random.uniform(0.05, 0.3)  # Higher ZCR
        spec_cent_var = np.random.uniform(1000, 15000)  # Higher spectral variance
        flatness = np.random.uniform(0.3, 1.0)  # Higher flatness
        
        human_data.append([duration, f0_var, zcr_mean, spec_cent_var, flatness, 0])
    
    # AI_GENERATED voice features (stable, lower variance)
    ai_data = []
    for _ in range(n_samples_per_class):
        duration = np.random.uniform(0.5, 30.0)
        f0_var = np.random.uniform(10, 300)  # Low pitch variance (stable)
        zcr_mean = np.random.uniform(0.01, 0.08)  # Lower ZCR
        spec_cent_var = np.random.uniform(100, 5000)  # Lower spectral variance
        flatness = np.random.uniform(0.1, 0.4)  # Lower flatness
        
        ai_data.append([duration, f0_var, zcr_mean, spec_cent_var, flatness, 1])
    
    data = np.array(human_data + ai_data)
    X = data[:, :-1]  # Features
    y = data[:, -1]   # Labels
    
    return X, y


def train_model(output_dir="voice_detector/models"):
    """Train and save the ML model."""
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating synthetic training data...")
    X, y = generate_training_data(n_samples_per_class=500)
    
    print(f"Training set: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"Class distribution: {np.sum(y == 0)} HUMAN, {np.sum(y == 1)} AI_GENERATED")
    
    # Train RandomForest
    print("\nTraining RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X, y)
    
    # Feature importance
    feature_names = ["duration", "f0_var", "zcr_mean", "spec_centroid_var", "flatness_mean"]
    importances = model.feature_importances_
    
    print("\nFeature Importance:")
    for name, importance in zip(feature_names, importances):
        print(f"  {name}: {importance:.4f}")
    
    # Evaluate on training data (synthetic, so high accuracy expected)
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)
    
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred)
    recall = recall_score(y, y_pred)
    f1 = f1_score(y, y_pred)
    
    print(f"\nTraining Metrics:")
    print(f"  Accuracy: {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print(f"  F1 Score: {f1:.4f}")
    
    # Train feature scaler
    scaler = StandardScaler()
    scaler.fit(X)
    
    # Save model and scaler
    model_path = os.path.join(output_dir, "voice_classifier.joblib")
    scaler_path = os.path.join(output_dir, "feature_scaler.joblib")
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"\n✅ Model saved to: {model_path}")
    print(f"✅ Scaler saved to: {scaler_path}")
    
    # Save metadata
    metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 100,
        "max_depth": 15,
        "feature_names": feature_names,
        "classes": ["HUMAN", "AI_GENERATED"],
        "training_samples": X.shape[0],
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "version": "1.0",
        "date": "2026-02-05"
    }
    
    metadata_path = os.path.join(output_dir, "model_metadata.joblib")
    joblib.dump(metadata, metadata_path)
    
    print(f"✅ Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    train_model()
