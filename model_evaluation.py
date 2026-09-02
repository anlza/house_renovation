import joblib
import pandas as pd
import numpy as np

from pathlib import Path

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error,
    r2_score
)

from sklearn.model_selection import (
    train_test_split,
    KFold,
    cross_val_score
)

from sklearn.preprocessing import LabelEncoder


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "dataset" / "house_renovation_dataset_20000.csv"

MODELS_DIR = BASE_DIR / "models"
# ============================================================
# LOAD DATASET
# ============================================================

df = pd.read_csv(DATA_PATH)

print("=" * 60)
print("DATASET LOADED")
print("=" * 60)
print(df.shape)
# ============================================================
# LABEL ENCODING
# ============================================================

categorical_cols = [

    "State",
    "City",
    "Region_Type",
    "Renovation_Type",
    "Quality_Grade",
    "Material_Quality",
    "Waterproofing_Required",
    "Season"

]

for col in categorical_cols:

    encoder = LabelEncoder()

    df[col] = encoder.fit_transform(
        df[col].astype(str)
    )
# ============================================================
# FEATURES
# ============================================================

FEATURES = [

    "House_Area_sqft",
    "Number_of_Rooms",
    "Number_of_Bathrooms",
    "Number_of_Floors",
    "House_Age",
    "Basement",

    "State",
    "City",
    "Region_Type",

    "Renovation_Type",
    "Quality_Grade",
    "Material_Quality",

    "Wall_Condition",
    "Roof_Condition",
    "Plumbing_Condition",
    "Electrical_Condition",

    "Waterproofing_Required",
    "Season",

    "Cement_Price",
    "Steel_Price",
    "Sand_Price",
    "Paint_Price",
    "Brick_Price",
    "Tile_Price",
    "Wood_Price"

]

X = df[FEATURES]

TARGETS = {

    "Cost": "Estimated_Renovation_Cost",
    "Labour": "Estimated_Labour_Cost",
    "Duration": "Estimated_Duration_Days"

}
# ============================================================
# MODEL EVALUATION FUNCTION
# ============================================================

def evaluate_model(name, model):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    target = TARGETS[name]

    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )

    predictions = model.predict(X_test)

    # -------------------------
    # Metrics
    # -------------------------

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    mape = mean_absolute_percentage_error(
        y_test,
        predictions
    ) * 100

    mape_based_score = 100 - mape

    r2 = r2_score(
        y_test,
        predictions
    )

    # -------------------------
    # Cross Validation
    # -------------------------

    cv = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42
    )

    cv_score = cross_val_score(
        model,
        X,
        y,
        cv=cv,
        scoring="r2"
    )

    # -------------------------
    # Display Results
    # -------------------------

    print(f"MAE           : {mae:,.2f}")
    print(f"RMSE          : {rmse:,.2f}")
    print(f"MAPE          : {mape:.2f}%")
    print(f"MAPE-based score: {mape_based_score:.2f}%")
    print(f"R² Score      : {r2:.4f}")
    print(f"5-Fold CV R²  : {cv_score.mean():.4f}")
# ============================================================
# LOAD MODELS
# ============================================================

# -------------------------
# Random Forest
# -------------------------

rf_cost = joblib.load(
    MODELS_DIR / "rf_cost.pkl"
)

rf_labour = joblib.load(
    MODELS_DIR / "rf_labour.pkl"
)

rf_duration = joblib.load(
    MODELS_DIR / "rf_duration.pkl"
)

# -------------------------
# Gradient Boosting
# -------------------------

gb_cost = joblib.load(
    MODELS_DIR / "gb_cost.pkl"
)

gb_labour = joblib.load(
    MODELS_DIR / "gb_labour.pkl"
)

gb_duration = joblib.load(
    MODELS_DIR / "gb_duration.pkl"
)

# -------------------------
# XGBoost
# -------------------------

xgb_cost = joblib.load(
    MODELS_DIR / "xgb_cost.pkl"
)

xgb_labour = joblib.load(
    MODELS_DIR / "xgb_labour.pkl"
)

xgb_duration = joblib.load(
    MODELS_DIR / "xgb_duration.pkl"
)
# ============================================================
# EVALUATION
# ============================================================

print("\n")
print("=" * 60)
print("RANDOM FOREST RESULTS")
print("=" * 60)

evaluate_model("Cost", rf_cost)
evaluate_model("Labour", rf_labour)
evaluate_model("Duration", rf_duration)


print("\n")
print("=" * 60)
print("GRADIENT BOOSTING RESULTS")
print("=" * 60)

evaluate_model("Cost", gb_cost)
evaluate_model("Labour", gb_labour)
evaluate_model("Duration", gb_duration)


print("\n")
print("=" * 60)
print("XGBOOST RESULTS")
print("=" * 60)

evaluate_model("Cost", xgb_cost)
evaluate_model("Labour", xgb_labour)
evaluate_model("Duration", xgb_duration)


# ============================================================
# BEST MODEL SUMMARY
# ============================================================

rf_scores = [
    cross_val_score(
        rf_cost,
        X,
        df[TARGETS["Cost"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        rf_labour,
        X,
        df[TARGETS["Labour"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        rf_duration,
        X,
        df[TARGETS["Duration"]],
        cv=5,
        scoring="r2"
    ).mean()
]

gb_scores = [
    cross_val_score(
        gb_cost,
        X,
        df[TARGETS["Cost"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        gb_labour,
        X,
        df[TARGETS["Labour"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        gb_duration,
        X,
        df[TARGETS["Duration"]],
        cv=5,
        scoring="r2"
    ).mean()
]

xgb_scores = [
    cross_val_score(
        xgb_cost,
        X,
        df[TARGETS["Cost"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        xgb_labour,
        X,
        df[TARGETS["Labour"]],
        cv=5,
        scoring="r2"
    ).mean(),

    cross_val_score(
        xgb_duration,
        X,
        df[TARGETS["Duration"]],
        cv=5,
        scoring="r2"
    ).mean()
]

rf_avg = np.mean(rf_scores)
gb_avg = np.mean(gb_scores)
xgb_avg = np.mean(xgb_scores)

print("\n")
print("=" * 60)
print("BEST MODEL SUMMARY")
print("=" * 60)

print(f"Random Forest Average R²      : {rf_avg:.4f}")
print(f"Gradient Boosting Average R²  : {gb_avg:.4f}")
print(f"XGBoost Average R²            : {xgb_avg:.4f}")

best_model = max(
    {
        "Random Forest": rf_avg,
        "Gradient Boosting": gb_avg,
        "XGBoost": xgb_avg
    },
    key=lambda x: {
        "Random Forest": rf_avg,
        "Gradient Boosting": gb_avg,
        "XGBoost": xgb_avg
    }[x]
)

print(f"\n🏆 Best Model : {best_model}")

print("\n")
print("=" * 60)
print("MODEL EVALUATION COMPLETED")
print("=" * 60)