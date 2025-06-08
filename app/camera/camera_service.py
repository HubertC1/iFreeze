import picamera
import io
import time
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

NGROK_URL_BASE = os.getenv('VITE_NGROK_URL_BASE', 'http://localhost:8000')
API_URL = NGROK_URL_BASE

class FridgeCamera:
    def __init__(self):
        self.camera = picamera.PiCamera()
        self.camera.resolution = (640, 480)
        self.camera.framerate = 30
        
    def capture_image(self):
        """Capture an image from the camera"""
        stream = io.BytesIO()
        self.camera.capture(stream, format='jpeg')
        stream.seek(0)
        return stream.getvalue()
    
    async def process_and_upload(self):
        """Capture image and send to API"""
        image_data = self.capture_image()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/fridge/image",
                data=image_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    def start_monitoring(self, interval=3600):  # Default: check every hour
        """Start continuous monitoring of the fridge"""
        while True:
            try:
                self.process_and_upload()
                time.sleep(interval)
            except Exception as e:
                print(f"Error in camera monitoring: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def __del__(self):
        self.camera.close()

if __name__ == "__main__":
    camera = FridgeCamera()
    camera.start_monitoring() 