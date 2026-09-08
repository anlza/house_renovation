# Lumina Nest

## AI-Powered House Renovation Budget Planner and Smart Material Recommendation System

Lumina Nest is an AI-powered house renovation planning system developed to help users estimate renovation costs, labour costs, and project duration based on house details and renovation requirements.

## Features

- User Registration and Login
- Renovation Cost Prediction
- Labour Cost Estimation
- Renovation Duration Prediction
- Support for Multiple Renovation Types
- Smart Material Recommendations
- Material Price Comparison
- Budget Optimization
- Explainable AI-Based Predictions
- Location-Based Material Planning
- PDF Report Generation

## Supported Renovation Types

1. Full House Renovation
2. Interior Renovation
3. Exterior Renovation
4. Kitchen Renovation
5. Bathroom Renovation
6. Painting
7. Flooring and Tiling
8. Roofing
9. Plumbing
10. Electrical Work

## Technologies Used

- Python
- Streamlit
- Pandas
- NumPy
- Scikit-learn
- XGBoost
- Plotly
- SHAP
- ReportLab

## Machine Learning Models

The system uses machine learning models for predicting:

- Estimated Renovation Cost
- Estimated Labour Cost
- Estimated Duration

Models used include:

- Random Forest Regressor
- Gradient Boosting Regressor
- XGBoost Regressor

## Project Structure

```text
Lumina_Nest/
│
├── auth_page/          # Authentication pages
├── dataset/            # Renovation dataset
├── models/             # Trained ML models
├── modules/            # Application modules
├── services/           # Supporting services
├── static/             # Static files
├── utils/              # Utility functions
│
├── auth.py             # Authentication logic
├── config.py           # Configuration
├── dashboard.py        # Main Streamlit application
├── dataset_generator.py
├── model_evaluation.py
├── train_models.py
├── requirements.txt
└── README.md
# Lumina Nest renovation planner

Run `pip install -r requirements.txt` and then `streamlit run dashboard.py` from this folder.

All application data is stored in `users.json`: users, projects, estimates, expenses, contractor quotes and password-reset verification records. No SQLite database is used.

The planning estimate is preliminary only. Confirm material rates, site conditions, contractor quotes and final logistics before committing work.
