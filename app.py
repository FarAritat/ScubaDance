import streamlit as st
import cv2
import mediapipe as mp
import time
import math
import os
import av
from streamlit_webrtc import webrtc_streamer
from database import add_userdata, login_user, update_high_score, get_high_score
from spotify_handler import SpotifyHandler

# --- INITIALIZATION ---
st.set_page_config(page_title="Scuba Dance Master", layout="wide")

# สร้างตัวแปรสำหรับ Mediapipe ไว้ใน Session State เพื่อให้เรียกใช้ใน Callback ได้
if 'mp_pose' not in st.session_state:
    st.session_state.mp_pose = mp.solutions.pose
    st.session_state.pose = st.session_state.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
    st.session_state.mp_draw = mp.solutions.drawing_utils

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'count' not in st.session_state: st.session_state.count = 0
if 'last_side' not in st.session_state: st.session_state.last_side = None

# --- SCUBA LOGIC ---
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

# --- WEBRTC CALLBACK ---
def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    img = cv2.flip(img, 1)
    results = st.session_state.pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    is_covering = False
    if results.pose_landmarks:
        st.session_state.mp_draw.draw_landmarks(img, results.pose_landmarks, st.session_state.mp_pose.POSE_CONNECTIONS)
        st.session_state.count, st.session_state.last_side, is_covering = calculate_scuba_logic(
            results.pose_landmarks.landmark, st.session_state.last_side, st.session_state.count
        )
    
    # วาด UI ลงบนภาพ
    color = (0, 255, 0) if is_covering else (0, 0, 255)
    cv2.putText(img, f"Score: {st.session_state.count}", (20, 50), 1, 2, (255, 255, 0), 2)
    cv2.putText(img, "DANCING!" if is_covering else "HOLD HAND TO MOUTH", (20, 100), 1, 1.5, color, 2)
    
    return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- UI SCREENS ---
def login_screen():
    st.title("🤿 Scuba Dance AI Login")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        u = st.text_input("User")
        p = st.text_input("Pass", type='password')
        if st.button("Login"):
            if login_user(u, p):
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
    with t2:
        nu, np = st.text_input("New User"), st.text_input("New Pass", type='password')
        if st.button("Sign Up"):
            if add_userdata(nu, np): st.success("Success!")

def game_screen():
    st.sidebar.metric("🏆 High Score", f"{get_high_score(st.session_state.username)}")
    if st.sidebar.button("Reset Score/Logout"):
        update_high_score(st.session_state.username, st.session_state.count)
        st.session_state.logged_in = False
        st.session_state.count = 0
        st.rerun()

    st.title(f"🕺 Scuba Dance: {st.session_state.username}")
    
    # Spotify Integration
    try:
        sp_h = SpotifyHandler()
        track_id = sp_h.search_scuba_music()
        st.components.v1.iframe(f"http://googleusercontent.com/spotify.com/5{track_id}", height=80)
    except: st.write("🎵 Spotify Connected")

    # กล้องแบบ WebRTC (สำหรับ Online Hosting)
    webrtc_streamer(
        key="scuba-dance",
        video_frame_callback=video_frame_callback,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )
    
    st.write(f"### 🔥 คะแนนปัจจุบัน: {st.session_state.count}")
    if st.button("บันทึกคะแนนสูงสุด"):
        update_high_score(st.session_state.username, st.session_state.count)
        st.balloons()

if __name__ == "__main__":
    if st.session_state.logged_in: game_screen()
    else: login_screen()