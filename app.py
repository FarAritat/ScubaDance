import streamlit as st
import cv2
import mediapipe as mp
import time
import math
import os
import av
import numpy as np
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
from database import add_userdata, login_user, update_high_score, get_high_score
from spotify_handler import SpotifyHandler

# --- INITIALIZATION ---
st.set_page_config(page_title="Scuba Dance Master", layout="wide")

# โหลด Model ครั้งเดียวและแชร์ใช้ทั้งแอป (ช่วยลดอาการค้าง)
@st.cache_resource
def load_pose_model():
    mp_pose = mp.solutions.pose
    return mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0,  # 0 = Lite (เร็วที่สุดสำหรับบนเว็บ)
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

pose = load_pose_model()
mp_draw = mp.solutions.drawing_utils

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
    
    # แปลงสีเป็น RGB เพื่อให้ Mediapipe อ่านได้
    results = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    is_covering = False
    if results.pose_landmarks:
        # วาดเส้น Skeleton (ลดเหลือแค่จุดสำคัญถ้ายังช้า)
        mp_draw.draw_landmarks(img, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        
        # คำนวณคะแนน
        new_count, new_side, is_covering = calculate_scuba_logic(
            results.pose_landmarks.landmark, 
            st.session_state.last_side, 
            st.session_state.count
        )
        
        # อัปเดต State (WebRTC ทำงานแยก Thread ต้องระวัง)
        st.session_state.count = new_count
        st.session_state.last_side = new_side
    
    # วาดคะแนนลงบนจอกล้อง
    color = (0, 255, 0) if is_covering else (0, 0, 255)
    cv2.putText(img, f"Score: {st.session_state.count}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    status_text = "DANCING!" if is_covering else "READY?"
    cv2.putText(img, status_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- UI SCREENS ---
def login_screen():
    st.title("🤿 Scuba Dance AI Login")
    tab1, tab2 = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
    with tab1:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type='password', key="login_pass")
        if st.button("เข้าสู่ระบบ"):
            if login_user(u, p):
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
            else: st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    with tab2:
        nu = st.text_input("New Username", key="reg_user")
        np = st.text_input("New Password", type='password', key="reg_pass")
        if st.button("สมัครสมาชิก"):
            if add_userdata(nu, np): st.success("สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
            else: st.error("ชื่อผู้ใช้นี้อาจมีผู้อื่นใช้ไปแล้ว")

def game_screen():
    st.sidebar.title(f"User: {st.session_state.username}")
    st.sidebar.metric("🏆 High Score", f"{get_high_score(st.session_state.username)}")
    
    if st.sidebar.button("Logout & Save"):
        update_high_score(st.session_state.username, st.session_state.count)
        st.session_state.logged_in = False
        st.session_state.count = 0
        st.rerun()

    st.title("🕺 Scuba Dance Challenge")
    
    # Spotify Integration
    try:
        sp_h = SpotifyHandler()
        track_id = sp_h.search_scuba_music()
        if track_id:
            st.components.v1.iframe(f"https://open.spotify.com/embed/track/{track_id}", height=80)
    except:
        st.info("🎵 Spotify Player Ready (เข้าสู่โหมดการเต้น)")

    # --- WEB RTC STREAMER ---
    webrtc_streamer(
        key="scuba-dance-v1",
        video_frame_callback=video_frame_callback,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={
            "video": {
                "width": {"ideal": 640},
                "height": {"ideal": 480},
                "frameRate": {"ideal": 20}
            },
            "audio": False,
        },
        async_processing=True, # ป้องกันภาพค้างขณะประมวลผล AI
    )
    
    st.markdown(f"## 🔥 คะแนนปัจจุบัน: {st.session_state.count}")
    
    if st.button("บันทึกคะแนนสูงสุด"):
        update_high_score(st.session_state.username, st.session_state.count)
        st.success(f"บันทึกคะแนน {st.session_state.count} เรียบร้อย!")
        st.balloons()

if __name__ == "__main__":
    if st.session_state.logged_in: game_screen()
    else: login_screen()