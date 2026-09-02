# Lumina Nest – AI-Powered House Renovation Planner

An MCA mini project that combines machine-learning based renovation estimates with renovation-specific material planning, exact work-site selection and supplier-to-site transportation planning.

## Main workflow
1. Register and log in.
2. Choose one of 10 renovation types.
3. Enter current house details.
4. Enter only the requirements relevant to the selected renovation.
5. Search and pin the exact work-site on the map.
6. Search and pin the material supplier/yard.
7. Choose material quality, finish quality, season and budget.
8. Review AI estimate, transparent material allocation, transportation, material comparison, guidance, PDF report and user history.

## Material logic
Only materials required by the selected renovation are shown.

Examples:
- **Painting:** Paint, Primer, Putty.
- **Flooring & Tiling:** Tiles, Tile Adhesive, Sand and minor Cement work.
- **Electrical Work:** Electrical Cable, Switches & Sockets, MCB & Conduit.
- **Plumbing:** PVC/CPVC Pipes, Plumbing Fittings and relevant Fixtures.
- **Roofing:** Cement, Steel, Sand and Waterproofing when waterproofing is selected.

The displayed planning rate is the same rate used to calculate the quantity and material cost. The application does not use `Not catalogued` as a rate for a calculated material.

## ML evaluation
Regression models are evaluated with MAE, RMSE, MAPE, MAPE-based score and R².

Current saved Gradient Boosting models were trained on the included 20,000-row dataset:
- Renovation cost R²: approximately **0.857**
- Labour cost R²: approximately **0.866**
- Duration R²: approximately **0.871**

These are synthetic-data evaluation results and are planning estimates, not guarantees of real contractor quotations.

## Run
```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

## Optional retraining
The ZIP already contains trained models matching the included dataset. Retrain only after changing the dataset:

```powershell
python train_models.py
```

## Notes
- Prediction history is stored inside each user record in `users.json`, not in the dataset folder.
- Exact map pins are used for transportation routing. If a pinned locality is not present in the ML training labels, a compatible trained location label is used only for ML encoding; the exact coordinates remain unchanged for routing.
- Reference material rates are planning values, not live supplier quotations.
