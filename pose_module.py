import cv2
import mediapipe as mp

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils

    def find_pose(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.pose.process(img_rgb)
        lm_list = []
        if results.pose_landmarks:
            self.mp_draw.draw_landmarks(img, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            for id, lm in enumerate(results.pose_landmarks.landmark):
                h, w, c = img.shape
                lm_list.append([id, int(lm.x * w), int(lm.y * h)])
        return img, lm_list