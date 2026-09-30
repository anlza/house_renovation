import joblib
from pathlib import Path
from functools import lru_cache
BASE_DIR=Path(__file__).resolve().parent.parent
MODELS_DIR=BASE_DIR/'models'
@lru_cache(maxsize=1)
def load_models():
    return {
        'encoders': joblib.load(MODELS_DIR/'label_encoders.pkl'),
        'features': joblib.load(MODELS_DIR/'feature_columns.pkl'),
        'cost': joblib.load(MODELS_DIR/'rf_cost.pkl'),
        'labour': joblib.load(MODELS_DIR/'rf_labour.pkl'),
        'duration': joblib.load(MODELS_DIR/'rf_duration.pkl'),
        'budget_status': joblib.load(MODELS_DIR/'rf_budget_status.pkl'),
        'classification_features': joblib.load(MODELS_DIR/'classification_feature_columns.pkl')
    }
