import os
import hashlib
from supabase import create_client, Client

# ดึงค่าจาก Secrets/Environment
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(URL, KEY)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_userdata(username, password):
    try:
        data = {"username": username, "password": make_hashes(password), "high_score": 0}
        supabase.table("userstable").insert(data).execute()
        return True
    except:
        return False

def login_user(username, password):
    res = supabase.table("userstable").select("password").eq("username", username).execute()
    if res.data:
        return check_hashes(password, res.data[0]['password'])
    return False

def update_high_score(username, new_score):
    res = supabase.table("userstable").select("high_score").eq("username", username).execute()
    if res.data:
        current_high = res.data[0]['high_score']
        if new_score > current_high:
            supabase.table("userstable").update({"high_score": new_score}).eq("username", username).execute()

def get_high_score(username):
    res = supabase.table("userstable").select("high_score").eq("username", username).execute()
    if res.data:
        return res.data[0]['high_score']
    return 0