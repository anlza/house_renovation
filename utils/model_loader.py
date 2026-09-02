import joblib
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"


@lru_cache(maxsize=1)
def load_models():

    return {

        "encoders": joblib.load(
            MODELS_DIR / "label_encoders.pkl"
        ),

        "features": joblib.load(
            MODELS_DIR / "feature_columns.pkl"
        ),

        # Gradient Boosting Models
        "cost": joblib.load(
            MODELS_DIR / "gb_cost.pkl"
        ),

        "labour": joblib.load(
            MODELS_DIR / "gb_labour.pkl"
        ),

        "duration": joblib.load(
            MODELS_DIR / "gb_duration.pkl"
        )

    }
