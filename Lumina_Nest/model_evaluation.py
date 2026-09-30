import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt

BASE_DIR=Path(__file__).resolve().parent
DATASET=BASE_DIR/'dataset'/'house_renovation_dataset_20000.csv'
MODELS=BASE_DIR/'models'
FEATURES=joblib.load(MODELS/'feature_columns.pkl')
CLASS_FEATURES=joblib.load(MODELS/'classification_feature_columns.pkl')
encoders=joblib.load(MODELS/'label_encoders.pkl')
df=pd.read_csv(DATASET).drop_duplicates().copy()
for c,e in encoders.items(): df[c]=e.transform(df[c].astype(str))
X=df[FEATURES]
_, X_test=train_test_split(X,test_size=.20,random_state=42,shuffle=True)
rows=[]
for name,target in {'Cost':'Estimated_Renovation_Cost','Labour':'Estimated_Labour_Cost','Duration':'Estimated_Duration_Days'}.items():
    model=joblib.load(MODELS/f'rf_{name.lower()}.pkl'); y=df.loc[X_test.index,target]; pred=model.predict(X_test)
    rows.append({'Model':f'Random Forest - {name}','MAE':round(mean_absolute_error(y,pred),2),'RMSE':round(np.sqrt(mean_squared_error(y,pred)),2),'MAPE':round(np.mean(np.abs((y-pred)/(y+1e-9)))*100,2),'R2':round(r2_score(y,pred),4)})
results=pd.DataFrame(rows); results.to_csv(MODELS/'model_results.csv',index=False)
# Classification evaluation on the same fixed stratified split used during training.
XC=df[CLASS_FEATURES]; y=df['Budget_Status']
_, XC_test, _, y_test=train_test_split(XC,y,test_size=.20,random_state=42,shuffle=True,stratify=y)
clf=joblib.load(MODELS/'rf_budget_status.pkl'); threshold=joblib.load(MODELS/'budget_status_threshold.pkl'); prob=clf.predict_proba(XC_test)[:,list(clf.classes_).index('Within Budget')]; pred=np.where(prob>=threshold,'Within Budget','Over Budget')
acc=accuracy_score(y_test,pred); prec=precision_score(y_test,pred,average='macro'); rec=recall_score(y_test,pred,average='macro'); f1=f1_score(y_test,pred,average='macro'); cm=confusion_matrix(y_test,pred,labels=['Within Budget','Over Budget'])
pd.DataFrame([{'Model':'Random Forest - Budget Status','Accuracy':round(acc,4),'Precision_Macro':round(prec,4),'Recall_Macro':round(rec,4),'F1_Macro':round(f1,4),'Threshold':threshold,'Within_Budget_Recall':round(recall_score(y_test,pred,pos_label='Within Budget'),4),'Within_Budget_F1':round(f1_score(y_test,pred,pos_label='Within Budget'),4)}]).to_csv(MODELS/'classification_results.csv',index=False)
pd.DataFrame(cm,index=['Actual Within Budget','Actual Over Budget'],columns=['Predicted Within Budget','Predicted Over Budget']).to_csv(MODELS/'budget_confusion_matrix.csv')
# Presentation-ready confusion matrix diagram.
fig, ax=plt.subplots(figsize=(7,5.2))
im=ax.imshow(cm)
ax.set_xticks([0,1],['Within Budget','Over Budget'])
ax.set_yticks([0,1],['Within Budget','Over Budget'])
ax.set_xlabel('Predicted class'); ax.set_ylabel('Actual class')
ax.set_title(f'Budget Status – Random Forest\nAccuracy: {acc*100:.2f}% | Macro F1: {f1*100:.2f}% | Macro Recall: {rec*100:.2f}%')
for i in range(2):
    for j in range(2): ax.text(j,i,str(cm[i,j]),ha='center',va='center')
fig.tight_layout(); fig.savefig(MODELS/'budget_confusion_matrix.png',dpi=180); plt.close(fig)
print(results.to_string(index=False)); print(f'Budget Status Accuracy={acc:.4f}, Macro Precision={prec:.4f}, Macro Recall={rec:.4f}, Macro F1={f1:.4f}'); print(cm)
