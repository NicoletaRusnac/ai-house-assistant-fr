import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import sqlite3
from flask import Flask, render_template, request, jsonify
from threading import Thread

# Flask app setup
app = Flask(__name__)
voice_enabled = True  # Default to enabled
try:
    with open("voice_settings.txt", "r", encoding="utf-8") as f:
        voice_enabled = f.read().strip() == "True"
except FileNotFoundError:
    pass
latest_person = "None"
picam2 = None
cv_scaler = 4
known_face_encodings = []
known_face_names = []
trigger_speech = None
face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0
detected_persons = set()  # Track detected persons in the current session
last_face_time = 0  # Track the last time a face was detected
NO_FACE_TIMEOUT = 10  # Reset session after 10 seconds with no faces

# Load encodings
def load_encodings():
    global known_face_encodings, known_face_names
    try:
        with open("encodings.pickle", "rb") as f:
            data = pickle.load(f)
        known_face_encodings = data["encodings"]
        known_face_names = data["names"]
        print("[INFO] Encodings loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load encodings: {e}")
        exit()

# Initialize camera and database
def init_system():
    global picam2
    try:
        print("[INFO] Initializing camera...")
        picam2 = Picamera2()
        print("[INFO] Configuring camera...")
        picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
        print("[INFO] Starting camera...")
        picam2.start()
        time.sleep(2)  # Allow camera to warm up
        print("[INFO] Camera initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Camera initialization failed: {e}")
        exit()
   
    # Initialize database
    try:
        print("[INFO] Initializing database...")
        conn = sqlite3.connect("database.db", check_same_thread=False)
        conn.execute("CREATE TABLE IF NOT EXISTS logbook (timestamp TEXT, name TEXT)")
        conn.commit()
        conn.close()
        print("[INFO] Database initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

# Draw results on the frame
def draw_results(frame):
    global face_locations, face_names
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler
        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), (244, 42, 3), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)
    return frame

# Calculate FPS
def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps

# Face recognition function
def recognize_face(frame):
    global latest_person, trigger_speech, detected_persons, last_face_time
    global face_locations, face_encodings, face_names
    try:
        print("[INFO] Resizing frame...")
        resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
       
        print("[INFO] Detecting faces...")
        face_locations = face_recognition.face_locations(rgb_resized_frame)
        if not face_locations:
            print("[INFO] No faces detected.")
            face_names = []
            return None
       
        # Update the last time a face was detected
        last_face_time = time.time()
        print(f"[DEBUG] Face detected, last_face_time updated to {last_face_time}")
       
        print("[INFO] Encoding faces...")
        face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')
        if not face_encodings:
            print("[INFO] No face encodings generated.")
            face_names = ["Unknown" for _ in range(len(face_locations))]
            return None
       
        face_names = []
        name = "Unknown"
       
        for face_encoding in face_encodings:
            print("[INFO] Comparing faces...")
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) == 0:
                print("[INFO] No face distances computed.")
                face_names.append("Unknown")
                continue
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                name = known_face_names[best_match_index]
            face_names.append(name)
       
        if not face_names:
            print("[INFO] No faces identified after comparison.")
            return None
       
        name = face_names[0]  # Take the first detected face
        print(f"[INFO] Identified name: {name}")
       
        # Notify and log if this person hasn't been detected in the current session
        print(f"[DEBUG] Current detected_persons: {detected_persons}")
        if name not in detected_persons:
            detected_persons.add(name)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect("database.db", check_same_thread=False)
            conn.execute("INSERT INTO logbook (timestamp, name) VALUES (?, ?)", (timestamp, name))
            conn.commit()
            conn.close()
            latest_person = name
            trigger_speech = f"Person detected: {name}" if voice_enabled else None
            print(f"[INFO] New person detected: {name}, trigger_speech set to: {trigger_speech}")
            return name
        else:
            print(f"[INFO] Person {name} already detected in this session.")
        return None
    except Exception as e:
        print(f"[ERROR] Face recognition failed: {e}")
        face_names = ["Unknown" for _ in range(len(face_locations))]
        return None

# Video loop (runs in a separate thread)
def video_loop():
    global trigger_speech, last_face_time, detected_persons
    last_face_time = time.time()  # Initialize the timer
   
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert for display
       
        # Always perform face recognition
        print("[DEBUG] Calling recognize_face()")
        recognize_face(frame)
       
        # Check if no faces have been detected for NO_FACE_TIMEOUT seconds
        if not face_locations:  # No faces in the current frame
            current_time = time.time()
            if (current_time - last_face_time) > NO_FACE_TIMEOUT:
                detected_persons.clear()
                last_face_time = current_time  # Reset the timer
                print("[INFO] No faces detected for 10 seconds, session reset.")
        else:
            last_face_time = time.time()  # Update timer if faces are present

        # Draw results and FPS
        display_frame = draw_results(frame)
        current_fps = calculate_fps()
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
       
        # Display the frame
        cv2.imshow('Video', display_frame)
       
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) == ord("q"):
            break
   
    # Cleanup
    cv2.destroyAllWindows()
    picam2.stop()

# Flask routes
@app.route("/", methods=["GET", "POST"])
def index():
    global voice_enabled, trigger_speech, detected_persons
    local_trigger_speech = None
    if request.method == "POST":
        if "scan" in request.form:
            detected_persons.clear()  # Reset detected persons on manual scan
            print("[INFO] Manual scan initiated, reset detected persons")
        elif "voice" in request.form:
            voice_enabled = request.form.get("voice") == "on"
            with open("voice_settings.txt", "w", encoding="utf-8") as f:
                f.write(str(voice_enabled))
   
    if trigger_speech:
        local_trigger_speech = trigger_speech
        trigger_speech = None  # Reset after use
        print(f"[DEBUG] Passing trigger_speech to template: {local_trigger_speech}")
    else:
        print("[DEBUG] No trigger_speech to pass to template.")
   
    return render_template("index.html", logs=get_logs(), latest_person=latest_person,
                         voice_enabled=voice_enabled, trigger_speech=local_trigger_speech)

@app.route("/get_status")
def get_status():
    return jsonify({"latest_person": latest_person})

def get_logs():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logbook ORDER BY timestamp DESC LIMIT 10")
    logs = cursor.fetchall()
    conn.close()
    return logs

if __name__ == "__main__":
    init_system()
    load_encodings()
    video_thread = Thread(target=video_loop, daemon=True)
    video_thread.start()
    app.run(host="0.0.0.0", port=5000)