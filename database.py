import os
import hashlib
from dotenv import load_dotenv # 1. ต้อง import ตัวนี้
from supabase import create_client, Client

# 2. สั่งโหลดไฟล์ .env (ถ้าอยู่บน Cloud มันจะข้ามบรรทัดนี้ไปเอง ไม่ต้องห่วง)
load_dotenv() 

# 3. ดึงค่าจาก Environment เท่านั้น (ห้ามเขียน URL/KEY ลงในนี้ตรงๆ)
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

# เช็กดักไว้ก่อนรัน เดี๋ยวมัน Error ยาว
if not URL or not KEY:
    raise ValueError("หา SUPABASE_URL หรือ KEY ไม่เจอ! เช็กไฟล์ .env ในเครื่อง หรือ Secrets บน Cloud ด่วน")

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
    # แก้ไข Logic นิดหน่อยเพื่อความชัวร์
    try:
        res = supabase.table("userstable").select("password").eq("username", username).execute()
        if res.data:
            return check_hashes(password, res.data[0]['password'])
    except:
        pass
    return False

def update_high_score(username, new_score):
    try:
        res = supabase.table("userstable").select("high_score").eq("username", username).execute()
        if res.data:
            current_high = res.data[0]['high_score']
            if new_score > current_high:
                supabase.table("userstable").update({"high_score": new_score}).eq("username", username).execute()
    except:
        pass

def get_high_score(username):
    try:
        res = supabase.table("userstable").select("high_score").eq("username", username).execute()
        if res.data:
            return res.data[0]['high_score']
    except:
        pass
    return 0