import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / 'dataset' / 'house_renovation_dataset_20000.csv'
MODELS_DIR = BASE_DIR / 'models'
MODELS_DIR.mkdir(exist_ok=True)

FEATURES = [
    'House_Area_sqft','Number_of_Rooms','Number_of_Bathrooms','Number_of_Floors','House_Age','Basement',
    'State','City','Region_Type','Renovation_Type','Quality_Grade','Material_Quality',
    'Wall_Condition','Roof_Condition','Plumbing_Condition','Electrical_Condition',
    'Waterproofing_Required','Season','Cement_Price','Steel_Price','Sand_Price','Paint_Price',
    'Brick_Price','Tile_Price','Wood_Price'
]
CLASS_FEATURES = ['Estimated_Renovation_Cost', 'Available_Budget_INR']
TARGETS = {
    'Cost': 'Estimated_Renovation_Cost',
    'Labour': 'Estimated_Labour_Cost',
    'Duration': 'Estimated_Duration_Days'
}
CATEGORICAL = [
    'State','City','Region_Type','Renovation_Type','Quality_Grade',
    'Material_Quality','Waterproofing_Required','Season'
]

if not DATASET_PATH.exists():
    raise FileNotFoundError(DATASET_PATH)

raw_df = pd.read_csv(DATASET_PATH)

# -----------------------------------------------------------------------------
# DATASET SUMMARY FOR DOCUMENTATION / VS CODE TERMINAL
# -----------------------------------------------------------------------------
num_records = len(raw_df)
num_attributes = raw_df.shape[1]
num_missing = int(raw_df.isna().sum().sum())
num_duplicates = int(raw_df.duplicated().sum())

print('\n' + '=' * 72)
print('LUMINA NEST - DATASET SUMMARY')
print('=' * 72)
print(f'Number of Records   : {num_records}')
print(f'Number of Attributes: {num_attributes}')
print(f'Missing Values      : {num_missing}')
print(f'Duplicate Records   : {num_duplicates}')
print('=' * 72)

# -----------------------------------------------------------------------------
# HANDLING MISSING VALUES AND CHECKING DUPLICATES
# -----------------------------------------------------------------------------
missing_values = raw_df.isna().sum()
num_duplicates_before_cleaning = int(raw_df.duplicated().sum())

print('\n' + '=' * 72)
print('LUMINA NEST - HANDLING MISSING VALUES')
print('=' * 72)
print('Missing Values in House Renovation Data:')
print(missing_values.to_string())

if num_missing == 0:
    print('\nNo missing values were found in any attribute.')
    print('Handling applied: No imputation required.')
else:
    print('\nMissing values were found and require preprocessing.')

print(f'\nDuplicate Records Found: {num_duplicates_before_cleaning}')
print('Duplicate records are removed before model training, if any.')
print('=' * 72)

# Remove duplicate records, if any
df = raw_df.drop_duplicates().copy()
required = FEATURES + list(TARGETS.values()) + ['Budget_Status', 'Available_Budget_INR']
for c in required:
    if c not in df.columns:
        raise ValueError(f'Missing column: {c}')

# Encode categorical features once and reuse the same encoders in the application.
encoders = {}
for c in CATEGORICAL:
    enc = LabelEncoder()
    df[c] = enc.fit_transform(df[c].astype(str))
    encoders[c] = enc
joblib.dump(encoders, MODELS_DIR / 'label_encoders.pkl')
joblib.dump(FEATURES, MODELS_DIR / 'feature_columns.pkl')
joblib.dump(CLASS_FEATURES, MODELS_DIR / 'classification_feature_columns.pkl')

# -----------------------------------------------------------------------------
# REGRESSION MODELS
# -----------------------------------------------------------------------------
X = df[FEATURES]
X_train, X_test = train_test_split(X, test_size=0.20, random_state=42, shuffle=True)
idx_train, idx_test = X_train.index, X_test.index

PARAMS = dict(
    n_estimators=120, min_samples_split=20, min_samples_leaf=10,
    max_features='sqrt', bootstrap=True, random_state=42, n_jobs=-1
)
DEPTHS = {'Cost': 7, 'Labour': 8, 'Duration': 20}
TARGET_PARAMS = {
    'Cost': PARAMS,
    'Labour': PARAMS,
    'Duration': dict(
        n_estimators=120, min_samples_split=6, min_samples_leaf=3,
        max_features='sqrt', bootstrap=True, random_state=42, n_jobs=-1
    )
}

rows = []
for name, target in TARGETS.items():
    model = RandomForestRegressor(max_depth=DEPTHS[name], **TARGET_PARAMS[name])
    model.fit(X_train, df.loc[idx_train, target])
    pred = model.predict(X_test)
    y = df.loc[idx_test, target]
    mae = mean_absolute_error(y, pred)
    rmse = np.sqrt(mean_squared_error(y, pred))
    r2 = r2_score(y, pred)
    mape = np.mean(np.abs((y - pred) / (y + 1e-9))) * 100
    joblib.dump(model, MODELS_DIR / f'rf_{name.lower()}.pkl')
    rows.append({
        'Model': f'Random Forest - {name}',
        'MAE': round(mae, 2),
        'RMSE': round(rmse, 2),
        'MAPE': round(mape, 2),
        'R2': round(r2, 4)
    })

regression_df = pd.DataFrame(rows)
regression_df.to_csv(MODELS_DIR / 'model_results.csv', index=False)

# -----------------------------------------------------------------------------
# BUDGET STATUS CLASSIFICATION
# -----------------------------------------------------------------------------
XC = df[CLASS_FEATURES]
XC_train, XC_test = train_test_split(
    XC, test_size=0.20, random_state=42, shuffle=True,
    stratify=df['Budget_Status']
)
ci_train, ci_test = XC_train.index, XC_test.index

clf = RandomForestClassifier(
    n_estimators=200, max_depth=6, min_samples_split=16,
    min_samples_leaf=10, max_features=2, class_weight='balanced',
    random_state=42, n_jobs=-1
)
clf.fit(XC_train, df.loc[ci_train, 'Budget_Status'])
yc = df.loc[ci_test, 'Budget_Status']
within_idx = list(clf.classes_).index('Within Budget')
prob = clf.predict_proba(XC_test)[:, within_idx]
CLASSIFICATION_THRESHOLD = 0.61
pc = np.where(prob >= CLASSIFICATION_THRESHOLD, 'Within Budget', 'Over Budget')

acc = accuracy_score(yc, pc)
prec = precision_score(yc, pc, average='macro')
rec = recall_score(yc, pc, average='macro')
f1 = f1_score(yc, pc, average='macro')
cm = confusion_matrix(yc, pc, labels=['Within Budget', 'Over Budget'])

joblib.dump(clf, MODELS_DIR / 'rf_budget_status.pkl')
label_encoder = LabelEncoder().fit(df['Budget_Status'])
joblib.dump(label_encoder, MODELS_DIR / 'budget_label_encoder.pkl')
joblib.dump(CLASSIFICATION_THRESHOLD, MODELS_DIR / 'budget_status_threshold.pkl')

classification = pd.DataFrame([{
    'Model': 'Random Forest - Budget Status',
    'Accuracy': round(acc, 4),
    'Precision_Macro': round(prec, 4),
    'Recall_Macro': round(rec, 4),
    'F1_Macro': round(f1, 4),
    'Threshold': CLASSIFICATION_THRESHOLD,
    'Within_Budget_Recall': round(recall_score(yc, pc, pos_label='Within Budget'), 4),
    'Within_Budget_F1': round(f1_score(yc, pc, pos_label='Within Budget'), 4)
}])
classification.to_csv(MODELS_DIR / 'classification_results.csv', index=False)

cm_df = pd.DataFrame(
    cm,
    index=['Actual Within Budget', 'Actual Over Budget'],
    columns=['Predicted Within Budget', 'Predicted Over Budget']
)
cm_df.to_csv(MODELS_DIR / 'budget_confusion_matrix.csv')

# -----------------------------------------------------------------------------
# PRINT OUTPUT FOR VS CODE TERMINAL
# -----------------------------------------------------------------------------
print('\n' + '=' * 72)
print('LUMINA NEST - MODEL EVALUATION')
print('=' * 72)
print('\nBUDGET STATUS CLASSIFICATION')
print('-' * 72)
print(f'Accuracy          : {acc * 100:.2f}%')
print(f'Precision (Macro) : {prec * 100:.2f}%')
print(f'Recall (Macro)    : {rec * 100:.2f}%')
print(f'F1 Score (Macro)  : {f1 * 100:.2f}%')
print('\nConfusion Matrix (Actual x Predicted)')
print(cm_df.to_string())

print('\n' + '=' * 72)
print('REGRESSION MODEL PERFORMANCE')
print('=' * 72)
print(regression_df.rename(columns={'R2': 'R²'}).to_string(index=False))
print('=' * 72)
print('\nTwo presentation images were saved in the models folder:')
print('1. budget_confusion_matrix.png')
print('2. regression_model_performance.png')

# -----------------------------------------------------------------------------
# PAGE 1: CONFUSION MATRIX ONLY
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 6.4))
im = ax.imshow(cm, cmap='Blues')
ax.set_xticks([0, 1], ['Within Budget', 'Over Budget'])
ax.set_yticks([0, 1], ['Within Budget', 'Over Budget'])
ax.set_xlabel('Predicted', fontsize=12, fontweight='bold')
ax.set_ylabel('Actual', fontsize=12, fontweight='bold')
ax.set_title(
    f'Budget Status Classification - Confusion Matrix\nAccuracy: {acc * 100:.2f}% | F1: {f1 * 100:.2f}%',
    fontsize=15, fontweight='bold', pad=16
)
for i in range(2):
    for j in range(2):
        value = int(cm[i, j])
        percentage = value / cm.sum() * 100
        ax.text(
            j, i, f'{value}\n({percentage:.1f}%)',
            ha='center', va='center', fontsize=15, fontweight='bold',
            color='white' if value > cm.max() * 0.45 else '#173457'
        )
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
fig.tight_layout()
fig.savefig(MODELS_DIR / 'budget_confusion_matrix.png', dpi=180, bbox_inches='tight')
plt.show(block=True)
plt.close(fig)

# -----------------------------------------------------------------------------
# PAGE 2: REGRESSION TABLE ONLY
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.8))
ax.axis('off')
ax.set_title('Regression Model Performance', fontsize=17, fontweight='bold',
             color='#173457', pad=18)

table_data = []
for _, r in regression_df.iterrows():
    model_name = r['Model'].replace('Random Forest - ', 'Random Forest – ')
    table_data.append([
        model_name,
        f"{r['MAE']:,.2f}",
        f"{r['RMSE']:,.2f}",
        f"{r['MAPE']:.2f}",
        f"{r['R2']:.4f}"
    ])

table = ax.table(
    cellText=table_data,
    colLabels=['Model', 'MAE', 'RMSE', 'MAPE (%)', 'R²'],
    cellLoc='center', colLoc='center',
    bbox=[0.04, 0.18, 0.92, 0.60],
    colWidths=[0.36, 0.16, 0.16, 0.14, 0.12]
)
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1, 2.0)
for (r, c), cell in table.get_celld().items():
    cell.set_edgecolor('#d9e2e2')
    if r == 0:
        cell.set_facecolor('#eaf6f1')
        cell.set_text_props(weight='bold', color='#173457')
    else:
        cell.set_facecolor('#ffffff')
        cell.set_text_props(color='#173457')

ax.text(
    0.5, 0.08,
    'Random Forest regression models | Fixed 80/20 test split | random_state = 42',
    ha='center', va='center', fontsize=10.5, color='#5d6878'
)
fig.tight_layout()
fig.savefig(MODELS_DIR / 'regression_model_performance.png', dpi=180, bbox_inches='tight')
plt.show(block=True)
plt.close(fig)

metrics_text = (
    'Lumina Nest — Budget Status Classification\n'
    'Algorithm: Random Forest Classifier\n'
    'Target: Budget_Status (Within Budget / Over Budget)\n'
    'Test split: stratified 80/20, random_state=42\n'
    f'Classification threshold: {CLASSIFICATION_THRESHOLD:.2f}\n'
    f'Accuracy: {acc * 100:.2f}%\n'
    f'Precision (Macro): {prec * 100:.2f}%\n'
    f'Recall (Macro): {rec * 100:.2f}%\n'
    f'F1 Score (Macro): {f1 * 100:.2f}%\n\n'
    'Confusion Matrix:\n'
    f'Actual Within Budget -> Predicted Within Budget: {cm[0,0]}; Predicted Over Budget: {cm[0,1]}\n'
    f'Actual Over Budget   -> Predicted Within Budget: {cm[1,0]}; Predicted Over Budget: {cm[1,1]}\n\n'
    'Note: Macro averages give equal weight to both Budget Status classes.\n'
    'The exact quantity-based budget comparison remains the final project status in the app.\n'
)
(MODELS_DIR / 'classification_metrics.txt').write_text(metrics_text, encoding='utf-8')
