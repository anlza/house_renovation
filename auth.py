# ============================================================
# auth.py
# Username + Password Authentication
# ============================================================

import json
import hashlib

from pathlib import Path
from datetime import datetime

USERS_FILE = Path(__file__).resolve().parent / "users.json"


# ============================================================
# LOAD USERS
# ============================================================

def _load_users():

    if USERS_FILE.exists():

        with open(USERS_FILE, "r") as f:

            return json.load(f)

    return {}


# ============================================================
# SAVE USERS
# ============================================================

def _save_users(users):

    with open(USERS_FILE, "w") as f:

        json.dump(users, f, indent=4)


# ============================================================
# HASH PASSWORD
# ============================================================

def _hash_password(password):

    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# CHECK USER
# ============================================================

def user_exists(username):

    username = username.strip().lower()

    return username in _load_users()


# ============================================================
# REGISTER USER
# ============================================================

def register_user(

    username,
    full_name,
    password

):

    username = username.strip().lower()

    full_name = full_name.strip()

    if len(username) < 3:

        return False, "Username must contain at least 3 characters."

    if len(password) < 6:

        return False, "Password must contain at least 6 characters."

    users = _load_users()

    if username in users:

        return False, "Username already exists."

    users[username] = {

        "full_name": full_name,

        "password": _hash_password(password),

        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        # Used once, on the first successful sign-in, to show a friendly
        # first-time greeting. Existing users simply get Welcome back.
        "first_login_pending": True,

        # All prediction history is stored inside this user record.
        "prediction_history": []

    }

    _save_users(users)

    return True, "Account created successfully."


# ============================================================
# LOGIN
# ============================================================

def verify_login(

    username,

    password

):

    username = username.strip().lower()

    users = _load_users()

    if username not in users:

        return False

    return (

        users[username]["password"]

        ==

        _hash_password(password)

    )


def verify_login_with_status(username, password):
    """Verify credentials and return whether this is the account's first login."""
    username = username.strip().lower()
    users = _load_users()
    if username not in users or users[username].get("password") != _hash_password(password):
        return False, False

    first_login = bool(users[username].get("first_login_pending", False))
    if first_login:
        users[username]["first_login_pending"] = False
        users[username]["last_login_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save_users(users)
    return True, first_login


# ============================================================
# RESET PASSWORD
# ============================================================

def reset_password(

    username,

    new_password

):

    username = username.strip().lower()

    users = _load_users()

    if username not in users:

        return False, "Username not found."

    users[username]["password"] = _hash_password(

        new_password

    )

    _save_users(users)

    return True, "Password updated successfully."


# ============================================================
# GET FULL NAME
# ============================================================

def get_full_name(

    username

):

    username = username.strip().lower()

    users = _load_users()

    return users.get(

        username,

        {}

    ).get(

        "full_name",

        username.title()

    )

# ============================================================
# USER PREDICTION HISTORY
# Stored inside users.json under each username
# ============================================================

def save_prediction_history(username, record):
    username = username.strip().lower()
    users = _load_users()
    if username not in users:
        return

    history = users[username].setdefault("prediction_history", [])
    history.insert(0, record)
    _save_users(users)


def get_prediction_history(username):
    username = username.strip().lower()
    users = _load_users()
    history = users.get(username, {}).get("prediction_history", [])
    return history if isinstance(history, list) else []
