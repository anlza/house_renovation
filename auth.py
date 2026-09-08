"""JSON-backed accounts and renovation records."""
import hashlib, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "users.json"; ITERATIONS = 260_000
def _now(): return datetime.now(timezone.utc)
def _stamp(): return _now().isoformat()
def _load():
    try: return json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"users": {}, "projects": [], "expenses": [], "quotes": [], "resets": []}
    except (OSError,json.JSONDecodeError): return {"users": {}, "projects": [], "expenses": [], "quotes": [], "resets": []}
def _save(data): DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
def _hash(password, salt=None):
    salt=salt or secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"
def _check(password, stored):
    try:
        a,i,s,d=stored.split("$"); actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(s),int(i)).hex()
        return a=="pbkdf2_sha256" and hmac.compare_digest(actual,d)
    except (ValueError,AttributeError): return False
def _user(data, username): return data["users"].get(username.strip().lower())
def _id(data, key): return max([x.get("id",0) for x in data.get(key,[])], default=0)+1
def user_exists(username): return bool(_user(_load(),username))
def register_user(username,full_name,password):
    data=_load(); username,full_name=username.strip().lower(),full_name.strip()
    if len(username)<3: return False,"Username must contain at least 3 characters."
    if len(password)<8: return False,"Password must contain at least 8 characters."
    if not full_name: return False,"Full name is required."
    if username in data["users"]: return False,"Username already exists."
    data["users"][username]={"full_name":full_name,"password_hash":_hash(password),"created_at":_stamp(),"first_login_pending":True,"history":[]}; _save(data); return True,"Account created successfully."
def verify_login_with_status(username,password):
    data=_load(); username=username.strip().lower(); user=_user(data,username)
    if not user or not _check(password,user["password_hash"]): return False,False
    first=bool(user.get("first_login_pending")); user["first_login_pending"]=False; user["last_login_at"]=_stamp(); _save(data); return True,first
def verify_login(username,password): return verify_login_with_status(username,password)[0]
def get_full_name(username):
    user=_user(_load(),username); return user.get("full_name",username.title()) if user else username.title()
def save_prediction_history(username,record):
    data=_load(); user=_user(data,username)
    if user: user.setdefault("history",[]).insert(0,record); _save(data)
def get_prediction_history(username): return _user(_load(),username).get("history",[]) if _user(_load(),username) else []
def create_project(username,name,project):
    data=_load(); ident=_id(data,"projects"); data["projects"].append({"id":ident,"username":username.strip().lower(),"name":name.strip() or "Untitled project","project":project,"created_at":_stamp()}); _save(data); return ident
def get_projects(username): return [x for x in _load()["projects"] if x["username"]==username.strip().lower()][::-1]
def add_expense(username,project_id,category,amount,expense_date,note):
    data=_load(); data["expenses"].append({"id":_id(data,"expenses"),"username":username.strip().lower(),"project_id":project_id,"category":category,"amount":float(amount),"expense_date":str(expense_date),"note":note,"created_at":_stamp()}); _save(data)
def get_expenses(username,project_id=None): return [x for x in _load()["expenses"] if x["username"]==username.strip().lower() and (not project_id or x["project_id"]==project_id)][::-1]
def add_quote(username,project_id,contractor_name,amount,duration_days,warranty,note):
    data=_load(); data["quotes"].append({"id":_id(data,"quotes"),"username":username.strip().lower(),"project_id":project_id,"contractor_name":contractor_name,"amount":float(amount),"duration_days":int(duration_days),"warranty":warranty,"note":note,"created_at":_stamp()}); _save(data)
def get_quotes(username,project_id=None): return sorted([x for x in _load()["quotes"] if x["username"]==username.strip().lower() and (not project_id or x["project_id"]==project_id)],key=lambda x:x["amount"])
def begin_password_reset(username):
    data=_load(); user=_user(data,username)
    if not user: return False,"If the account exists, a verification code has been sent.",None
    code=f"{secrets.randbelow(1_000_000):06d}"; data["resets"]=[r for r in data["resets"] if r["username"]!=username.strip().lower()]; data["resets"].append({"username":username.strip().lower(),"code_hash":hashlib.sha256(code.encode()).hexdigest(),"expires_at":(_now()+timedelta(minutes=15)).isoformat()}); _save(data); return True,"Verification code created. It expires in 15 minutes.",code
def complete_password_reset(username,code,new_password):
    data=_load(); username=username.strip().lower(); user=_user(data,username); reset=next((r for r in data["resets"] if r["username"]==username),None)
    if not user or len(new_password)<8: return False,"Use a password of at least 8 characters."
    if not reset or _now()>datetime.fromisoformat(reset["expires_at"]) or not hmac.compare_digest(hashlib.sha256(code.strip().encode()).hexdigest(),reset["code_hash"]): return False,"Verification code is invalid or expired."
    user["password_hash"]=_hash(new_password); data["resets"].remove(reset); _save(data); return True,"Password updated successfully."
