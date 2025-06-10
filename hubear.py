import board
import neopixel
import RPi.GPIO as GPIO
import cv2
import time
import os
import subprocess
# Add Flask imports
from flask import Flask, jsonify
import threading

#LED
NUM_PIXELS = 8
pixels = neopixel.NeoPixel(board.D18, NUM_PIXELS, brightness=0.3, auto_write=True)

#GPIO
BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#api
API = "https://dae2-140-112-25-46.ngrok/"
API_TAKE_PHOTO = "api/check-take-photo"
API_SET_TAKE_PHOTO = "api/check-set-take-photo"
API_SEND_PHOTO = "fridge/image"

#take photo detect
WATCH_DIR = "~"
TRIGGER_NAME = "take_photo.trigger"

#save picture 
SAVE_DIR = "/home/team5/i_fridge/photo"
os.makedirs(SAVE_DIR, exist_ok=True)

#camera initialize
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

previous_state = GPIO.input(BUTTON_PIN)

#LED flash
def flash_led(times=3, color=(255, 255, 255), delay=0.1):
    for _ in range(times):
        pixels.fill(color)
        time.sleep(delay)
        pixels.fill((0, 0, 0))
        time.sleep(delay)

def take_photo():
    flash_led(times=3, color=(255,255,255), delay=0.1)
    for _ in range(5):
        cam.read()
        time.sleep(0.05)

    ret, frame = cam.read()
    if ret:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(SAVE_DIR, f"photo_{timestamp}.jpg")
        cv2.imwrite(filename, frame)

    try:
        result = subprocess.run(
                ["curl", "-F", f"file=@{filename}", API+API_SEND_PHOTO],
                check = True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
                )
        print("upload successfully")
        print("server reply: ", result.stdout)

    except subprocess.CalledProcessError as e:
        print("Failed to Upload")
        print(e.stderr)

# --- Flask server setup ---
app = Flask(__name__)

@app.route("/trigger-photo", methods=["GET"])
def trigger_photo():
    threading.Thread(target=take_photo, daemon=True).start()
    return jsonify({"status": "photo process started"})

def run_server():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

# Start Flask server in a background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
# --- End Flask server setup ---

print("Start runnung...")

try:
    while True:
        current_state = GPIO.input(BUTTON_PIN)
        
        trigger_path = os.path.join( TRIGGER_NAME)
        if os.path.exists(trigger_path):
            print("detected! Take a photo!")
            take_photo()
            os.remove(trigger_path)

            time.sleep(0.05)

        if current_state == GPIO.LOW and previous_state == GPIO.HIGH:
            print("Button pressed + LED OFF + Flash + Take photo")

            pixels.fill((0, 0, 0))

            take_photo()

        elif current_state == GPIO.HIGH:
            pixels.fill((255,255,255))

        previous_state = current_state
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Exit requested")
    cam.release()
    pixels.fill((0,0,0))
    GPIO.cleanup()


