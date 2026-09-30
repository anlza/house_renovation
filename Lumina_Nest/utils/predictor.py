def predict(models, data):
    
    cost = models["cost"].predict(data)[0]

    labour = models["labour"].predict(data)[0]

    duration = models["duration"].predict(data)[0]

    return {

        "cost": round(float(cost), 2),

        "labour": round(float(labour), 2),

        "duration": int(round(duration))

    }

def predict_budget_status(models, estimated_cost, available_budget):
    """Predict the AI budget-status class from the AI cost benchmark and user budget."""
    import pandas as pd
    frame = pd.DataFrame([{'Estimated_Renovation_Cost': float(estimated_cost),
                           'Available_Budget_INR': float(available_budget)}])
    model = models['budget_status']
    probability = None
    if hasattr(model, 'predict_proba'):
        probs = model.predict_proba(frame[models['classification_features']])[0]
        within_idx = list(model.classes_).index('Within Budget')
        probability = float(probs[within_idx])
        try:
            import joblib
            from pathlib import Path
            threshold = float(joblib.load(Path(__file__).resolve().parents[1] / 'models' / 'budget_status_threshold.pkl'))
        except Exception:
            threshold = 0.50
        label = 'Within Budget' if probability >= threshold else 'Over Budget'
    else:
        label = model.predict(frame[models['classification_features']])[0]
    return str(label), probability
