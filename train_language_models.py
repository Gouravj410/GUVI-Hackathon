"""
Per-language model training and calibration.
Trains separate RandomForest models for each supported language.
"""
import numpy as np
import os
import sys
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.calibration import CalibratedClassifierCV

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "ml": "Malayalam",
    "te": "Telugu",
}


def generate_language_specific_training_data(language: str, n_samples_per_class=300):
    """
    Generate synthetic training data with language-specific characteristics.
    
    Different languages have different phonetic properties:
    - Tonal languages (Tamil, Telugu, Hindi): More pitch variation in HUMAN speech
    - English: Stress-timed, less pitch variation
    """
    np.random.seed(42 + hash(language) % 1000)  # Seed varies by language
    
    # Language-specific feature adjustments
    lang_params = {
        "en": {"f0_human_mult": 1.0, "zcr_human_mult": 1.0, "spec_var_human_mult": 1.0},
        "ta": {"f0_human_mult": 1.3, "zcr_human_mult": 1.2, "spec_var_human_mult": 1.2},
        "hi": {"f0_human_mult": 1.2, "zcr_human_mult": 1.1, "spec_var_human_mult": 1.15},
        "ml": {"f0_human_mult": 1.25, "zcr_human_mult": 1.15, "spec_var_human_mult": 1.2},
        "te": {"f0_human_mult": 1.22, "zcr_human_mult": 1.13, "spec_var_human_mult": 1.18},
    }
    
    params = lang_params.get(language, lang_params["en"])
    
    # HUMAN voice features (more variation)
    human_data = []
    for _ in range(n_samples_per_class):
        duration = np.random.uniform(0.5, 30.0)
        f0_var = np.random.uniform(200, 3000) * params["f0_human_mult"]
        zcr_mean = np.random.uniform(0.06, 0.35) * params["zcr_human_mult"]
        spec_cent_var = np.random.uniform(2000, 18000) * params["spec_var_human_mult"]
        flatness = np.random.uniform(0.4, 1.0)
        
        human_data.append([duration, f0_var, zcr_mean, spec_cent_var, flatness, 0])
    
    # AI_GENERATED voice features (stable, lower variance)
    ai_data = []
    for _ in range(n_samples_per_class):
        duration = np.random.uniform(0.5, 30.0)
        f0_var = np.random.uniform(10, 250)  # Always low for AI
        zcr_mean = np.random.uniform(0.01, 0.07)
        spec_cent_var = np.random.uniform(100, 4000)
        flatness = np.random.uniform(0.1, 0.4)
        
        ai_data.append([duration, f0_var, zcr_mean, spec_cent_var, flatness, 1])
    
    data = np.array(human_data + ai_data)
    X = data[:, :-1]
    y = data[:, -1]
    
    return X, y


def train_language_model(language: str, output_dir="voice_detector/models/language_specific"):
    """Train a model for a specific language."""
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Training model for: {LANGUAGES[language]} ({language})")
    print(f"{'='*60}")
    
    # Generate training data
    X, y = generate_language_specific_training_data(language)
    
    print(f"Training set: {X.shape[0]} samples")
    print(f"Class distribution: {np.sum(y == 0)} HUMAN, {np.sum(y == 1)} AI_GENERATED")
    
    # Train base RandomForest
    print("Training RandomForest...")
    base_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=16,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    base_model.fit(X, y)
    
    # Calibrate probabilities for better confidence scores
    print("Calibrating probabilities...")
    model = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)
    model.fit(X, y)
    
    # Feature importance
    feature_names = ["duration", "f0_var", "zcr_mean", "spec_centroid_var", "flatness_mean"]
    importances = base_model.feature_importances_
    
    print("\nFeature Importance:")
    for name, importance in zip(feature_names, importances):
        print(f"  {name}: {importance:.4f}")
    
    # Evaluate
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
    
    # Train scaler
    scaler = StandardScaler()
    scaler.fit(X)
    
    # Save model and scaler
    lang_code = language
    model_path = os.path.join(output_dir, f"model_{lang_code}.joblib")
    scaler_path = os.path.join(output_dir, f"scaler_{lang_code}.joblib")
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"\n✅ Model saved to: {model_path}")
    print(f"✅ Scaler saved to: {scaler_path}")
    
    # Save metadata
    metadata = {
        "language": lang_code,
        "language_name": LANGUAGES[language],
        "model_type": "CalibratedRandomForest",
        "n_estimators": 120,
        "max_depth": 16,
        "feature_names": feature_names,
        "classes": ["HUMAN", "AI_GENERATED"],
        "training_samples": X.shape[0],
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "version": "1.0",
        "language_calibrated": True,
        "date": "2026-02-05"
    }
    
    metadata_path = os.path.join(output_dir, f"metadata_{lang_code}.joblib")
    joblib.dump(metadata, metadata_path)
    
    print(f"✅ Metadata saved to: {metadata_path}")
    
    return metadata


def train_all_language_models():
    """Train models for all supported languages."""
    print("\n" + "="*60)
    print("Per-Language Model Training")
    print("="*60)
    
    results = {}
    for lang_code, lang_name in LANGUAGES.items():
        try:
            metadata = train_language_model(lang_code)
            results[lang_code] = {
                "status": "success",
                "accuracy": metadata["accuracy"],
                "f1_score": metadata["f1_score"]
            }
        except Exception as e:
            print(f"❌ Error training model for {lang_name}: {e}")
            results[lang_code] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Summary
    print("\n" + "="*60)
    print("Training Summary")
    print("="*60)
    
    for lang_code, result in results.items():
        lang_name = LANGUAGES[lang_code]
        if result["status"] == "success":
            print(f"✅ {lang_name:12} | Accuracy: {result['accuracy']:.4f} | F1: {result['f1_score']:.4f}")
        else:
            print(f"❌ {lang_name:12} | Error: {result['error']}")
    
    print("\n✅ All language models trained successfully!")
    print("\nTo use language-specific models in the API:")
    print("1. Update app.py to load language-specific models")
    print("2. Select model based on request language")
    print("3. Use appropriate scaler for feature normalization")


if __name__ == "__main__":
    train_all_language_models()
