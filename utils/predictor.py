def predict(models, data):
    
    cost = models["cost"].predict(data)[0]

    labour = models["labour"].predict(data)[0]

    duration = models["duration"].predict(data)[0]

    return {

        "cost": round(float(cost), 2),

        "labour": round(float(labour), 2),

        "duration": int(round(duration))

    }