import cv2
from ultralytics import YOLO
import sys
import requests
import threading
import time
import json
from flask import Flask, request, Response
from flask_socketio import SocketIO, emit
from predict import YOLOTracker
import logging

# TEST_MODE = False
TEST_MODE = True

# Suppress Flask's default request logging
if not TEST_MODE:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)



app= Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

latest_class_name = None

def generate_mjpg_stream(tracker):
    while True:
        frame = tracker.get_latest_frame()
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(1 / 30)

@app.route('/recognize', methods=['POST'])
def recognize():
    global latest_class_name
    data = request.get_json()
    if 'class_name' not in data:
        return {"error": "Missing class_name in request"}, 400

    class_name = data['class_name']
    latest_class_name = class_name
    print(f"Received recognized class: {class_name}", end="\r", flush=True)

    return {"message": f"Class '{class_name}' recognized successfully"}, 200

@app.route('/recognized_class', methods=['GET'])
def get_recognized_class():
    if latest_class_name is None:
        response = {"message": "No class has been recognized yet"}
    else:
        response = {"class_name": latest_class_name}
    
    html_response = f"""
    <html>
        <head>
            
            <style>
                pre {{
                    font-size: 100px;
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <pre>{latest_class_name}</pre>
        </body>
    </html>
    """

    return html_response, 200
    # return response, 200

@app.route('/mjpg_stream', methods=['GET'])
def mjpg_stream():
    return Response(generate_mjpg_stream(tracker), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    def run_server():
        socketio.run(app, host="0.0.0.0", port=5000)

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # tracker = YOLOTracker("runs/detect/train_6/weights/model.pt", test_mode=False)
    tracker = YOLOTracker("runs/detect/train_l/weights/best.pt", test_mode=TEST_MODE)
    tracker.start_tracking()
    
