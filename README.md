# Lumina Nest

## AI-Powered House Renovation Budget Planner

Lumina Nest is an AI-powered house renovation planning system that helps users estimate:

- Renovation Cost
- Labour Cost
- Renovation Duration

The system supports interactive renovation planning based on the user's selected renovation requirements.

## Renovation Types

1. Full House Renovation
2. Interior Renovation
3. Exterior Renovation
4. Kitchen Renovation
5. Bathroom Renovation
6. Painting
7. Flooring & Tiling
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
- Folium
- OpenPyXL
- ReportLab

## Main Features

- Interactive Renovation Planning
- Renovation Cost Prediction
- Labour Cost Prediction
- Duration Prediction
- Renovation-Specific Requirements
- Full House Work Selection
- Material Planning
- Location and Map Support
- Data Visualization
- PDF Report Generation
- User Authentication

## How to Run

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python -m streamlit run dashboard.py
```

The application will open in your web browser.

## Project Structure

```text
house_renovation/
├── dataset/
├── models/
├── modules/
├── services/
├── static/
├── utils/
├── auth.py
├── config.py
├── dashboard.py
├── dataset_generator.py
├── train_models.py
├── requirements.txt
└── README.md
```

## Project Objective

The objective of Lumina Nest is to provide a real-world interactive AI renovation planning system that helps users understand renovation requirements, estimate costs, plan materials, and make better renovation decisions.
