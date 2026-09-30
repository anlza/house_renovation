# Lumina Nest

## AI-Powered House Renovation Budget Planner

Lumina Nest is an AI-assisted house renovation planning and budgeting system. It combines Random Forest estimates for labour and duration with quantity-based material costing, supplier-to-site transportation planning, budget analysis, and expense tracking.

### Main Features
- User registration, login and password reset
- Renovation-specific work-scope and existing-quantity capture
- Quantity-based material planning with wastage
- Random Forest labour, duration, and independent cost benchmark
- Multiple renovation types with work-specific inputs
- Supplier-to-work-site route and transport planning
- Smart material recommendations and reference price comparison
- Budget planning, contingency reserve, PDF reports and prediction history
- Expense tracking for comparing planned and actual spending

### Machine Learning Algorithm
**Random Forest Regressor** is the single machine-learning algorithm used in this project. Three Random Forest regression models are trained for:
1. Estimated Renovation Cost
2. Estimated Labour Cost
3. Estimated Duration

The reported R² is calculated on a fixed 80/20 train-test split. The model configuration uses moderate tree depth and minimum leaf size to reduce overfitting. Actual R² depends on the dataset and training run; it is not artificially fixed to a target percentage.

### Project Structure
```text
Lumina_Nest/
├── auth_page/
├── dataset/
├── models/
├── modules/
├── services/
├── static/
├── utils/
├── auth.py
├── dashboard.py
├── model_evaluation.py
├── train_models.py
└── requirements.txt
```

Run:
```bash
pip install -r requirements.txt
python train_models.py
```

Running the training script also opens the presentation-ready evaluation dashboard (regression table, classification metrics, confusion matrix and classification report) and saves it as `models/model_evaluation_dashboard.png`.

```bash
streamlit run dashboard.py
```


## Final renovation input design
The planner asks only renovation-specific, homeowner-friendly questions. Contractor-only measurements such as exact pipe length, cable length, socket counts and leakage-point counts are estimated internally from the selected work and affected areas. Waterproofing is asked only where relevant (such as bathroom, roofing and exterior work), not as a generic plumbing question. Seasonal planning is not exposed in the user interface.


### Real-world work quantities
For selected renovation work, the planner collects practical quantities such as affected area, pipe length, fixture counts, electrical points, cabinet count, countertop area, roofing area, waterproofing area and interior/exterior work area. Existing quantities describe the current house; only the paired replacement/addition/work quantity is charged. Material quantities are calculated from those work measurements with wastage allowances.

### Hybrid estimation architecture
The application deliberately separates two estimates:
- **AI benchmark:** Random Forest predicts renovation cost from the trained house/location/condition feature set. It is shown for comparison and is not added to the final total.
- **Quantity-based renovation cost:** selected work quantities are converted into material quantities and priced using the reference catalogue. This is the material component used in the final budget.
- **AI labour and duration:** Random Forest estimates are used for labour cost and project duration.
- **Logistics:** transportation is calculated independently from the confirmed material-site and work-site route, estimated load, vehicle mileage, fuel and loading/unloading.

The result is a **planning estimate, not a contractor quotation**. Reference material rates, site conditions, contractor charges, taxes and actual quantities can vary by location and time.

### Dataset note
The included 20,000-row dataset is a synthetic, domain-based training dataset created for the academic project. It should be described transparently as synthetic data rather than as a survey of 20,000 real houses.


## Budget Status Classification

Lumina Nest includes a separate Random Forest classification model for **Budget Status** with two classes: **Within Budget** and **Over Budget**. The classifier uses the AI renovation-cost benchmark and the user's available budget as inputs.

Evaluation uses a fixed stratified 80/20 test split. The reported classification metrics are **macro-averaged**, so both Budget Status classes receive equal weight. Current test metrics are **83.30% accuracy, 88.01% macro precision, 78.16% macro recall, and 80.10% macro F1**.

A calibrated probability threshold of 0.61 is stored in `models/budget_status_threshold.pkl` and used consistently by the application. The confusion-matrix diagram is stored at `models/budget_confusion_matrix.png`.

The classification output is an AI budget-status estimate. The application's final project status remains the exact arithmetic comparison between the detailed quantity-based project total and the user's budget, so the classifier cannot silently override the calculated result.

For supervised classification, the dataset includes a synthetic `Available_Budget_INR` planning field. This was generated for the academic dataset because a large labelled real-world budget-status dataset was not available; it is not presented as collected household survey data.


## Regression Model Performance (Print/PPT Table)

| Model | MAE | RMSE | MAPE (%) | R² |
|---|---:|---:|---:|---:|
| Random Forest – Cost | 102484.85 | 143795.82 | 33.64 | **0.8339** |
| Random Forest – Labour | 70606.53 | 100647.89 | 34.45 | **0.8377** |
| Random Forest – Duration | 6.64 | 8.88 | 11.43 | **0.8358** |

R² values correspond to 83.39%, 83.77%, and 83.58% respectively.


## Security and deployment notes

- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes; plaintext passwords are never written to `users.json`.
- Account data is stored in `users.json`, which is excluded from Git through `.gitignore`. A fresh clone creates it on first use.
- The reset flow stores only a SHA-256 hash of the one-time verification code, applies expiry and attempt limits, and does not display the code in the normal UI.
- `LUMINA_DATA_FILE` can be set as an environment variable when account data should live outside the project directory.
- No API keys, database passwords, or cloud credentials are hardcoded in the current project configuration. The values in `config.py` are application/domain constants, not secrets.
- For production deployment, connect password-reset delivery to a verified email/SMS provider and store provider credentials in environment variables or a secret manager.
- The included 20,000-row CSV is retained for the academic/offline demo. For production deployment, the dataset can instead be downloaded from the approved project data source or stored in object storage.
- Generated Python cache files and local account data are intentionally excluded from the distributable ZIP.
