import streamlit as st
import cv2
import mediapipe as mp
import time
import math
import os
import av
import numpy as np
import threading
from streamlit_webrtc import webrtc_streamer, RTCConfiguration, WebRtcMode
from database import add_userdata, login_user, update_high_score, get_high_score
from spotify_handler import SpotifyHandler

# --- INITIALIZATION ---
st.set_page_config(page_title="Scuba Dance Master", layout="wide")

# ใช้ Lock เพื่อป้องกัน Thread ตีกันเวลาอัปเดตคะแนน
lock = threading.Lock()
if 'count' not in st.session_state: st.session_state.count = 0
if 'last_side' not in st.session_state: st.session_state.last_side = None

@st.cache_resource
def load_pose_model():
    return mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1, # ใช้ 1 เพราะ Cloud มีไฟล์อยู่แล้ว ไม่ต้องดาวน์โหลดใหม่
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

pose = load_pose_model()

# --- SCUBA LOGIC ---
def calculate_scuba_logic(lm, last_side, count):
    nose_x = lm[0].x
    mouth_center_x = (lm[9].x + lm[10].x) / 2
    mouth_center_y = (lm[9].y + lm[10].y) / 2
    dist_l = math.hypot(lm[15].x - mouth_center_x, lm[15].y - mouth_center_y)
    dist_r = math.hypot(lm[16].x - mouth_center_x, lm[16].y - mouth_center_y)
    
    threshold = 0.12 
    is_covering = dist_l < threshold or dist_r < threshold
    
    if is_covering:
        # ใช้มือข้างที่ไม่ป้องปากมาเต้น
        dancing_hand_x = lm[16].x if dist_l < threshold else lm[15].x
        current_side = "Left" if dancing_hand_x < nose_x else "Right"
        if last_side is not None and last_side != current_side:
            count += 1
        last_side = current_side
    return count, last_side, is_covering

# --- WEBRTC CALLBACK ---
def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    img = cv2.flip(img, 1)
    
    results = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    with lock: # ล็อค Thread เพื่อป้องกันอาการค้าง
        if results.pose_landmarks:
            st.session_state.count, st.session_state.last_side, is_covering = calculate_scuba_logic(
                results.pose_landmarks.landmark, 
                st.session_state.last_side, 
                st.session_state.count
            )
            
            # วาด UI แบบเบาบาง (แค่คะแนน)
            color = (0, 255, 0) if is_covering else (0, 0, 255)
            cv2.putText(img, f"Score: {st.session_state.count}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.circle(img, (20, 50), 5, color, -1)
            
    return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- UI SCREENS ---
def login_screen():
    st.title("🤿 Scuba Dance AI Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u = st.text_input("User", key="l_u")
        p = st.text_input("Pass", type='password', key="l_p")
        if st.button("Login"):
            if login_user(u, p):
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
    with tab2:
        nu, np = st.text_input("New User"), st.text_input("New Pass", type='password')
        if st.button("Register"):
            if add_userdata(nu, np): st.success("Success!")

def game_screen():
    # --- SIDEBAR: เพลงและสถิติ ---
    st.sidebar.title(f"🕺 {st.session_state.username}")
    st.sidebar.metric("🏆 High Score", get_high_score(st.session_state.username))
    
    st.sidebar.markdown("---")
    st.sidebar.write("🎵 Music Player")
    try:
        sp_h = SpotifyHandler()
        track_id = sp_h.search_scuba_music()
        st.sidebar.components.v1.iframe(f"https://open.spotify.com/embed/track/{track_id}", height=80)
    except:
        st.sidebar.write("Spotify Offline")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- MAIN STAGE ---
    st.title("Scuba Dance Master")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        webrtc_streamer(
            key="scuba-v3",
            mode=WebRtcMode.SENDRECV,
            video_frame_callback=video_frame_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={
                "video": {"width": 320, "height": 240, "frameRate": 15}, # ต่ำแต่ลื่น!
                "audio": False
            },
            async_processing=True,
        )

    with col2:
        st.metric("🔥 Score", st.session_state.count)
        if st.button("Save Score"):
            update_high_score(st.session_state.username, st.session_state.count)
            st.balloons()

if __name__ == "__main__":
    if st.session_state.logged_in: game_screen()
    else: login_screen()