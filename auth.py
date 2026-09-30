"""JSON-backed accounts and renovation records."""
import hashlib, hmac, json, os, re, secrets, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_FILE = Path(os.getenv("LUMINA_DATA_FILE", str(Path(__file__).resolve().parent / "users.json")))
ITERATIONS = 260_000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
MAX_NAME_LENGTH = 100
MAX_PASSWORD_LENGTH = 128
def _now(): return datetime.now(timezone.utc)
def _stamp(): return _now().isoformat()
def _default_data():
    return {"users": {}, "projects": [], "expenses": [], "resets": []}

def _load():
    """Load users.json and normalize older/list-based formats safely."""
    default = _default_data()
    try:
        if not DATA_FILE.exists():
            return default
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        # Older versions may have stored users as a top-level list.
        if isinstance(raw, list):
            users = {}
            for item in raw:
                if isinstance(item, dict) and item.get("username"):
                    record = dict(item)
                    username = str(record.pop("username")).strip().lower()
                    users[username] = record
            return {"users": users, "projects": [], "expenses": [], "resets": []}
        if not isinstance(raw, dict):
            return default
        data = dict(raw)
        data.setdefault("users", {})
        data.setdefault("projects", [])
        data.setdefault("expenses", [])
        data.setdefault("resets", [])
        if not isinstance(data["users"], dict):
            data["users"] = {}
        return data
    except (OSError, json.JSONDecodeError, TypeError):
        return default
def _save(data):
    """Persist account data atomically so an interrupted write cannot corrupt users.json."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    fd, temp_name = tempfile.mkstemp(prefix=".users_", suffix=".tmp", dir=str(DATA_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)
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
def register_user(username, full_name, password):
    data = _load()
    username = username.strip().lower()
    full_name = " ".join(full_name.strip().split())

    if not USERNAME_RE.fullmatch(username):
        return False, "Username must be 3–30 characters and use only letters, numbers, ., _, or -."
    if not full_name:
        return False, "Full name is required."
    if len(full_name) > MAX_NAME_LENGTH:
        return False, f"Full name must be at most {MAX_NAME_LENGTH} characters."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    if username in data["users"]:
        return False, "Username already exists."

    data["users"][username] = {
        "full_name": full_name,
        "password_hash": _hash(password),
        "created_at": _stamp(),
        "first_login_pending": True,
        "history": [],
    }
    _save(data)
    return True, "Account created successfully."
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
def begin_password_reset(username):
    data = _load()
    username = username.strip().lower()
    user = _user(data, username)
    if not USERNAME_RE.fullmatch(username) or not user:
        return False, "If the account exists, a verification code has been sent.", None

    now = _now()
    recent = [
        r for r in data["resets"]
        if r.get("username") == username
        and r.get("created_at")
        and now - datetime.fromisoformat(r["created_at"]) < timedelta(minutes=10)
    ]
    if len(recent) >= 3:
        return False, "Too many reset requests. Please try again later.", None

    code = f"{secrets.randbelow(1_000_000):06d}"
    data["resets"] = [
        r for r in data["resets"]
        if r.get("username") != username
        or now - datetime.fromisoformat(r.get("expires_at", now.isoformat())) > timedelta(minutes=15)
    ]
    data["resets"].append({
        "username": username,
        "code_hash": hashlib.sha256(code.encode()).hexdigest(),
        "created_at": _stamp(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
        "attempts": 0,
    })
    _save(data)
    return True, "Verification code created. It expires in 15 minutes.", code
def complete_password_reset(username, code, new_password):
    data = _load()
    username = username.strip().lower()
    user = _user(data, username)
    reset = next((r for r in data["resets"] if r.get("username") == username), None)

    if not user or len(new_password) < 8:
        return False, "Use a password of at least 8 characters."
    if len(new_password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    if not reset or _now() > datetime.fromisoformat(reset["expires_at"]):
        return False, "Verification code is invalid or expired."

    if int(reset.get("attempts", 0)) >= 5:
        data["resets"].remove(reset)
        _save(data)
        return False, "Too many verification attempts. Please request a new code."

    expected = hashlib.sha256(code.strip().encode()).hexdigest()
    if not hmac.compare_digest(expected, reset["code_hash"]):
        reset["attempts"] = int(reset.get("attempts", 0)) + 1
        _save(data)
        return False, "Verification code is invalid or expired."

    user["password_hash"] = _hash(new_password)
    data["resets"].remove(reset)
    _save(data)
    return True, "Password updated successfully."
