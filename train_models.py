# ============================================================
# train_models.py
# AI-Powered House Renovation Budget Planner
# ============================================================

import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from sklearn.model_selection import (
    train_test_split,
    KFold,
    cross_val_score
)

from sklearn.preprocessing import LabelEncoder

from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from xgboost import XGBRegressor


print("=" * 70)
print("AI HOUSE RENOVATION MODEL TRAINING")
print("=" * 70)

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR /
    "dataset" /
    "house_renovation_dataset_20000.csv"
)

MODELS_DIR = (
    BASE_DIR /
    "models"
)

MODELS_DIR.mkdir(exist_ok=True)

print(f"\nDataset : {DATASET_PATH}")
print(f"Models  : {MODELS_DIR}")

# ============================================================
# CHECK DATASET
# ============================================================

if not DATASET_PATH.exists():

    raise FileNotFoundError(
        "Dataset not found!\n"
        "Run dataset_generator.py first."
    )
# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading Dataset...")

df = pd.read_csv(DATASET_PATH)

print("✓ Dataset Loaded Successfully")

# ============================================================
# DATASET INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("DATASET INFORMATION")
print("=" * 70)

print(f"Rows              : {len(df):,}")
print(f"Columns           : {len(df.columns)}")
print(f"Dataset Shape     : {df.shape}")

# ============================================================
# DATA QUALITY CHECK
# ============================================================

missing_values = df.isnull().sum().sum()
duplicate_rows = df.duplicated().sum()

print(f"\nMissing Values    : {missing_values}")
print(f"Duplicate Rows    : {duplicate_rows}")

# ============================================================
# REMOVE DUPLICATES (IF ANY)
# ============================================================

if duplicate_rows > 0:

    df = df.drop_duplicates()

    print(f"\n✓ Removed {duplicate_rows} Duplicate Rows")

else:

    print("✓ No Duplicate Rows Found")

# ============================================================
# CHECK REQUIRED TARGET COLUMNS
# ============================================================

required_targets = [

    "Estimated_Renovation_Cost",
    "Estimated_Labour_Cost",
    "Estimated_Duration_Days"

]

missing_targets = [

    col
    for col in required_targets
    if col not in df.columns

]

if missing_targets:

    raise ValueError(
        f"\nMissing Target Columns : {missing_targets}"
    )

print("\n✓ Target Columns Verified")

# ============================================================
# DATA PREVIEW
# ============================================================

print("\nFirst Five Records\n")

print(df.head())

print("\n" + "=" * 70)
# ============================================================
# LABEL ENCODING
# ============================================================

print("\nEncoding Categorical Columns...")

categorical_columns = [

    "State",
    "City",
    "Region_Type",
    "Renovation_Type",
    "Quality_Grade",
    "Material_Quality",
    "Waterproofing_Required",
    "Season"

]

label_encoders = {}

for column in categorical_columns:

    encoder = LabelEncoder()

    df[column] = encoder.fit_transform(
        df[column].astype(str)
    )

    label_encoders[column] = encoder

print("✓ Categorical Encoding Completed")

# ============================================================
# SAVE LABEL ENCODERS
# ============================================================

joblib.dump(

    label_encoders,

    MODELS_DIR / "label_encoders.pkl"

)

print("✓ Label Encoders Saved Successfully")

print("=" * 70)
# ============================================================
# INPUT FEATURES
# ============================================================

print("\nPreparing Features...")

FEATURES = [

    # House Details
    "House_Area_sqft",
    "Number_of_Rooms",
    "Number_of_Bathrooms",
    "Number_of_Floors",
    "House_Age",
    "Basement",

    # Location
    "State",
    "City",
    "Region_Type",

    # Renovation Details
    "Renovation_Type",
    "Quality_Grade",
    "Material_Quality",

    # House Condition
    "Wall_Condition",
    "Roof_Condition",
    "Plumbing_Condition",
    "Electrical_Condition",

    # Other Features
    "Waterproofing_Required",
    "Season",

    # Material Prices
    "Cement_Price",
    "Steel_Price",
    "Sand_Price",
    "Paint_Price",
    "Brick_Price",
    "Tile_Price",
    "Wood_Price"

]

# ============================================================
# VERIFY FEATURE COLUMNS
# ============================================================

missing_features = [

    feature
    for feature in FEATURES
    if feature not in df.columns

]

if missing_features:

    raise ValueError(
        f"Missing Feature Columns : {missing_features}"
    )

print("✓ All Feature Columns Verified")

# ============================================================
# TARGET VARIABLES
# ============================================================

TARGET_COST = "Estimated_Renovation_Cost"
TARGET_LABOUR = "Estimated_Labour_Cost"
TARGET_DURATION = "Estimated_Duration_Days"

print("✓ Target Variables Selected")

# ============================================================
# CREATE INPUT & OUTPUT DATA
# ============================================================

X = df[FEATURES]

y_cost = df[TARGET_COST]

y_labour = df[TARGET_LABOUR]

y_duration = df[TARGET_DURATION]

print(f"\nFeature Matrix Shape : {X.shape}")

print(f"Cost Samples      : {len(y_cost):,}")
print(f"Labour Samples    : {len(y_labour):,}")
print(f"Duration Samples  : {len(y_duration):,}")

# ============================================================
# SAVE FEATURE LIST
# ============================================================

joblib.dump(

    FEATURES,

    MODELS_DIR / "feature_columns.pkl"

)

print("\n✓ Feature List Saved")

print("=" * 70)
# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

print("\nPreparing Training and Testing Data...")

X_train, X_test = train_test_split(

    X,

    test_size=0.20,

    random_state=42,

    shuffle=True

)

# ============================================================
# SPLIT TARGET VARIABLES
# ============================================================

train_index = X_train.index

test_index = X_test.index

y_cost_train = y_cost.loc[train_index]
y_cost_test = y_cost.loc[test_index]

y_labour_train = y_labour.loc[train_index]
y_labour_test = y_labour.loc[test_index]

y_duration_train = y_duration.loc[train_index]
y_duration_test = y_duration.loc[test_index]

# ============================================================
# TRAIN / TEST INFORMATION
# ============================================================

print("\nTrain-Test Split Completed")

print(f"Training Samples : {len(X_train):,}")
print(f"Testing Samples  : {len(X_test):,}")

print("Training Ratio   : 80%")
print("Testing Ratio    : 20%")

print("=" * 70)
# ============================================================
# RANDOM FOREST MODEL TRAINING
# ============================================================

print("\n" + "=" * 70)
print("TRAINING RANDOM FOREST MODELS")
print("=" * 70)

# ============================================================
# COST MODEL
# ============================================================

rf_cost = RandomForestRegressor(

    n_estimators=100,

    max_depth=10,

    min_samples_split=10,

    min_samples_leaf=5,

    max_features="sqrt",

    bootstrap=True,

    random_state=42,

    n_jobs=-1

)

print("\nTraining Cost Model...")

rf_cost.fit(
    X_train,
    y_cost_train
)

# ============================================================
# LABOUR MODEL
# ============================================================

rf_labour = RandomForestRegressor(

    n_estimators=100,

    max_depth=10,

    min_samples_split=10,

    min_samples_leaf=5,

    max_features="sqrt",

    bootstrap=True,

    random_state=42,

    n_jobs=-1

)

print("Training Labour Model...")

rf_labour.fit(
    X_train,
    y_labour_train
)

# ============================================================
# DURATION MODEL
# ============================================================

rf_duration = RandomForestRegressor(

    n_estimators=100,

    max_depth=10,

    min_samples_split=10,

    min_samples_leaf=5,

    max_features="sqrt",

    bootstrap=True,

    random_state=42,

    n_jobs=-1

)

print("Training Duration Model...")

rf_duration.fit(
    X_train,
    y_duration_train
)

print("\n✓ Random Forest Models Trained Successfully")

print("=" * 70)
# ============================================================
# GRADIENT BOOSTING MODEL TRAINING
# ============================================================

print("\n" + "=" * 70)
print("TRAINING GRADIENT BOOSTING MODELS")
print("=" * 70)

# ============================================================
# COST MODEL
# ============================================================

gb_cost = GradientBoostingRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_samples_split=10,

    min_samples_leaf=5,

    subsample=0.80,

    random_state=42

)

print("\nTraining Cost Model...")

gb_cost.fit(
    X_train,
    y_cost_train
)

# ============================================================
# LABOUR MODEL
# ============================================================

gb_labour = GradientBoostingRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_samples_split=10,

    min_samples_leaf=5,

    subsample=0.80,

    random_state=42

)

print("Training Labour Model...")

gb_labour.fit(
    X_train,
    y_labour_train
)

# ============================================================
# DURATION MODEL
# ============================================================

gb_duration = GradientBoostingRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_samples_split=10,

    min_samples_leaf=5,

    subsample=0.80,

    random_state=42

)

print("Training Duration Model...")

gb_duration.fit(
    X_train,
    y_duration_train
)

print("\n✓ Gradient Boosting Models Trained Successfully")

print("=" * 70)
# ============================================================
# XGBOOST MODEL TRAINING
# ============================================================

print("\n" + "=" * 70)
print("TRAINING XGBOOST MODELS")
print("=" * 70)

# ============================================================
# COST MODEL
# ============================================================

xgb_cost = XGBRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_child_weight=5,

    subsample=0.80,

    colsample_bytree=0.80,

    reg_alpha=0.5,

    reg_lambda=1.0,

    objective="reg:squarederror",

    random_state=42,

    n_jobs=-1

)

print("\nTraining Cost Model...")

xgb_cost.fit(
    X_train,
    y_cost_train
)

# ============================================================
# LABOUR MODEL
# ============================================================

xgb_labour = XGBRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_child_weight=5,

    subsample=0.80,

    colsample_bytree=0.80,

    reg_alpha=0.5,

    reg_lambda=1.0,

    objective="reg:squarederror",

    random_state=42,

    n_jobs=-1

)

print("Training Labour Model...")

xgb_labour.fit(
    X_train,
    y_labour_train
)

# ============================================================
# DURATION MODEL
# ============================================================

xgb_duration = XGBRegressor(

    n_estimators=100,

    learning_rate=0.05,

    max_depth=3,

    min_child_weight=5,

    subsample=0.80,

    colsample_bytree=0.80,

    reg_alpha=0.5,

    reg_lambda=1.0,

    objective="reg:squarederror",

    random_state=42,

    n_jobs=-1

)

print("Training Duration Model...")

xgb_duration.fit(
    X_train,
    y_duration_train
)

print("\n✓ XGBoost Models Trained Successfully")

print("=" * 70)
# ============================================================
# SAVE ALL TRAINED MODELS
# ============================================================

print("\n" + "=" * 70)
print("SAVING TRAINED MODELS")
print("=" * 70)

# ============================================================
# RANDOM FOREST MODELS
# ============================================================

joblib.dump(
    rf_cost,
    MODELS_DIR / "rf_cost.pkl"
)

joblib.dump(
    rf_labour,
    MODELS_DIR / "rf_labour.pkl"
)

joblib.dump(
    rf_duration,
    MODELS_DIR / "rf_duration.pkl"
)

print("✓ Random Forest Models Saved")

# ============================================================
# GRADIENT BOOSTING MODELS
# ============================================================

joblib.dump(
    gb_cost,
    MODELS_DIR / "gb_cost.pkl"
)

joblib.dump(
    gb_labour,
    MODELS_DIR / "gb_labour.pkl"
)

joblib.dump(
    gb_duration,
    MODELS_DIR / "gb_duration.pkl"
)

print("✓ Gradient Boosting Models Saved")

# ============================================================
# XGBOOST MODELS
# ============================================================

joblib.dump(
    xgb_cost,
    MODELS_DIR / "xgb_cost.pkl"
)

joblib.dump(
    xgb_labour,
    MODELS_DIR / "xgb_labour.pkl"
)

joblib.dump(
    xgb_duration,
    MODELS_DIR / "xgb_duration.pkl"
)

print("✓ XGBoost Models Saved")

# ============================================================
# SAVE LABEL ENCODERS & FEATURE LIST
# ============================================================

joblib.dump(
    label_encoders,
    MODELS_DIR / "label_encoders.pkl"
)

joblib.dump(
    FEATURES,
    MODELS_DIR / "feature_columns.pkl"
)

print("✓ Label Encoders Saved")

print("✓ Feature List Saved")

print("\nAll Models Saved Successfully.")

print("=" * 70)
# ============================================================
# MODEL EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("MODEL EVALUATION")
print("=" * 70)


def evaluate_model(model_name, model, X_test, y_test):

    prediction = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        prediction
    )

    mse = mean_squared_error(
        y_test,
        prediction
    )

    rmse = np.sqrt(mse)

    r2 = r2_score(
        y_test,
        prediction
    )

    mape = np.mean(
        np.abs(
            (y_test - prediction) /
            (y_test + 1e-9)
        )
    ) * 100

    mape_based_score = max(
        0,
        100 - mape
    )

    return {

        "Model": model_name,

        "MAE": round(mae, 2),

        "RMSE": round(rmse, 2),

        "MAPE": round(mape, 2),

        "MAPE_Based_Score": round(mape_based_score, 2),

        "R2": round(r2, 4)

    }


results = []

# ============================================================
# RANDOM FOREST
# ============================================================

results.append(
    evaluate_model(
        "RF Cost",
        rf_cost,
        X_test,
        y_cost_test
    )
)

results.append(
    evaluate_model(
        "RF Labour",
        rf_labour,
        X_test,
        y_labour_test
    )
)

results.append(
    evaluate_model(
        "RF Duration",
        rf_duration,
        X_test,
        y_duration_test
    )
)

# ============================================================
# GRADIENT BOOSTING
# ============================================================

results.append(
    evaluate_model(
        "GB Cost",
        gb_cost,
        X_test,
        y_cost_test
    )
)

results.append(
    evaluate_model(
        "GB Labour",
        gb_labour,
        X_test,
        y_labour_test
    )
)

results.append(
    evaluate_model(
        "GB Duration",
        gb_duration,
        X_test,
        y_duration_test
    )
)

# ============================================================
# XGBOOST
# ============================================================

results.append(
    evaluate_model(
        "XGB Cost",
        xgb_cost,
        X_test,
        y_cost_test
    )
)

results.append(
    evaluate_model(
        "XGB Labour",
        xgb_labour,
        X_test,
        y_labour_test
    )
)

results.append(
    evaluate_model(
        "XGB Duration",
        xgb_duration,
        X_test,
        y_duration_test
    )
)

# ============================================================
# DISPLAY RESULTS
# ============================================================

results_df = pd.DataFrame(results)

print("\n")
print(results_df)

results_df.to_csv(

    MODELS_DIR /
    "model_results.csv",

    index=False

)

print("\n✓ Model Evaluation Saved")

print("=" * 70)
# ============================================================
# 5-FOLD CROSS VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("5-FOLD CROSS VALIDATION")
print("=" * 70)

kf = KFold(

    n_splits=5,

    shuffle=True,

    random_state=42

)

cv_models = {

    "Random Forest": rf_cost,

    "Gradient Boosting": gb_cost,

    "XGBoost": xgb_cost

}

cv_results = []

# A representative fixed sample keeps 5-fold validation practical while
# still reporting a reproducible generalisation estimate for the 20,000-row dataset.
cv_sample_size = min(6000, len(df))
cv_data = df.sample(n=cv_sample_size, random_state=42)
X_cv = cv_data[FEATURES]
y_cost_cv = cv_data[TARGET_COST]

print(f"Cross-validation sample : {cv_sample_size:,} records")

for model_name, model in cv_models.items():

    scores = cross_val_score(

        model,

        X_cv,

        y_cost_cv,

        cv=kf,

        scoring="r2",

        n_jobs=1

    )

    mean_score = scores.mean()

    std_score = scores.std()

    print(

        f"{model_name:<20}"
        f" Mean R² : {mean_score:.4f}"
        f"   Std : {std_score:.4f}"

    )

    cv_results.append({

        "Model": model_name,

        "Mean_R2": round(mean_score, 4),

        "Std": round(std_score, 4)

    })

cv_df = pd.DataFrame(cv_results)

cv_df.to_csv(

    MODELS_DIR / "cross_validation.csv",

    index=False

)

print("\n✓ Cross Validation Report Saved")

# ============================================================
# BEST MODEL SELECTION
# ============================================================

print("\n" + "=" * 70)
print("BEST MODEL SELECTION")
print("=" * 70)

best_model = cv_df.loc[
    cv_df["Mean_R2"].idxmax()
]

print(f"Best Model : {best_model['Model']}")
print(f"Mean R²    : {best_model['Mean_R2']}")

print("=" * 70)
# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

print(f"""
Dataset                : {DATASET_PATH.name}

Rows                   : {len(df):,}

Input Features         : {len(FEATURES)}

Regression Targets     : 3

Algorithms Used
------------------------
Random Forest Regressor
Gradient Boosting Regressor
XGBoost Regressor

Total Models Saved     : 9

Models Directory
------------------------
{MODELS_DIR}

Saved Model Files
------------------------
rf_cost.pkl
rf_labour.pkl
rf_duration.pkl

gb_cost.pkl
gb_labour.pkl
gb_duration.pkl

xgb_cost.pkl
xgb_labour.pkl
xgb_duration.pkl

Additional Files
------------------------
label_encoders.pkl
feature_columns.pkl
model_results.csv
cross_validation.csv
""")

print("=" * 70)
print("MODEL TRAINING COMPLETED SUCCESSFULLY")
print("=" * 70)
