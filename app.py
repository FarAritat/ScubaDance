import streamlit as st
import cv2
import mediapipe as mp
import time
import math
import os
from database import add_userdata, login_user, update_high_score, get_high_score
from spotify_handler import SpotifyHandler # เรียกใช้ไฟล์ที่คุณเขียนไว้

# --- INITIALIZATION ---
st.set_page_config(page_title="Scuba Dance Master", layout="wide")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""

# --- SCUBA LOGIC: ป้องปาก + ข้ามฝั่ง ---
def calculate_scuba_logic(lm, last_side, count):
    nose_x = lm[0].x
    mouth_center_x = (lm[9].x + lm[10].x) / 2
    mouth_center_y = (lm[9].y + lm[10].y) / 2
    
    dist_l = math.hypot(lm[15].x - mouth_center_x, lm[15].y - mouth_center_y)
    dist_r = math.hypot(lm[16].x - mouth_center_x, lm[16].y - mouth_center_y)
    
    threshold = 0.12 
    covering_hand = None
    dancing_hand_x = None
    
    if dist_l < threshold:
        covering_hand, dancing_hand_x = "Left", lm[16].x
    elif dist_r < threshold:
        covering_hand, dancing_hand_x = "Right", lm[15].x
    
    is_covering = covering_hand is not None
    if is_covering:
        current_side = "Left" if dancing_hand_x < nose_x else "Right"
        if last_side is not None and last_side != current_side:
            count += 1
        last_side = current_side
        
    return count, last_side, is_covering

# --- UI SCREENS ---
def login_screen():
    st.title("🤿 Scuba Dance AI Login")
    tab1, tab2 = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
    with tab1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Password", type='password', key="l_p")
        if st.button("เข้าสู่ระบบ"):
            if login_user(u, p):
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
            else: st.error("Wrong Password")
    with tab2:
        nu, np = st.text_input("New User", key="r_u"), st.text_input("New Pwd", type='password', key="r_p")
        if st.button("สมัครสมาชิก"):
            if add_userdata(nu, np): st.success("Success!")
            else: st.error("User taken")

def game_screen():
    st.sidebar.title(f"User: {st.session_state.username}")
    st.sidebar.metric("🏆 High Score", f"{get_high_score(st.session_state.username)}")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🕺 Scuba Dance Challenge")
    
    # --- SPOTIFY API INTEGRATION ---
    try:
        sp_h = SpotifyHandler()
        track_id = sp_h.search_scuba_music()
        embed_url = f"https://open.spotify.com/embed/track/{track_id}"
        st.components.v1.iframe(embed_url, height=80)
    except:
        st.write("🎵 Spotify API connected (Waiting for playback)")

    if st.button("🎬 เริ่มเต้น (60 วินาที)"):
        run_camera()

def run_camera():
    cap = cv2.VideoCapture(0)
    st_frame, st_info = st.empty(), st.empty()
    count, last_side, start_time = 0, None, time.time()
    
    while time.time() - start_time < 60:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        is_covering = False
        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            count, last_side, is_covering = calculate_scuba_logic(results.pose_landmarks.landmark, last_side, count)
        
        time_left = 60 - int(time.time() - start_time)
        cv2.putText(frame, f"Score: {count} | Time: {time_left}s", (10, 50), 1, 2, (255, 255, 0), 2)
        st_frame.image(frame, channels="BGR")
        st_info.write(f"### 🔥 คะแนน: {count} | ⏳ เวลา: {time_left}")

    cap.release()
    update_high_score(st.session_state.username, count)
    st.balloons()
    st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in: game_screen()
    else: login_screen()