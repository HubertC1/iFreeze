from flask import Flask, request, jsonify
import os
import requests
import shutil
import json
from werkzeug.utils import secure_filename
from object_detection import detect_objects
from change_detection import check_matching_objects
from threading import Thread

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
RESULT_DIR = './result'
JSON_DIR = os.path.join(RESULT_DIR, 'json')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuration
UPLOAD_URL = 'https://dae2-140-112-25-46.ngrok-free.app/upload/zip'

def process_image(img_path):
    save_dir = './'
    # img_filename = 'fruit.png'  # Remove hardcoded filename
    # img_path = os.path.join(save_dir, img_filename)  # Use provided img_path
    
    # Process JSON files
    json_path = os.path.join(JSON_DIR, 'new.json')
    old_json_path = os.path.join(JSON_DIR, 'old.json')
    
    # Rename existing new.json to old.json if it exists
    if os.path.exists(json_path):
        os.rename(json_path, old_json_path)
    
    # Run object detection
    detect_objects(img_path=img_path, json_path=json_path, save_dir=RESULT_DIR)
    print("object_detect")
    # Run change detection if old.json exists
    if os.path.exists(old_json_path):
        check_matching_objects(old_json=old_json_path, new_json=json_path, save_dir=JSON_DIR)
    print("match check")
    # Create zip file
    zip_filename = 'data.zip'
    shutil.make_archive('data', 'zip', RESULT_DIR)
    print("data.zip save")
    # Upload results
    try:
        with open(zip_filename, 'rb') as f:
            files = {
                'file': (zip_filename, f, 'application/zip')
            }
            upload_response = requests.post(UPLOAD_URL, files=files)
            print("post issue")
            if upload_response.status_code == 200:
                return {
                    'message': 'Processing completed successfully',
                    'upload_response': upload_response.text
                }
            else:
                return {
                    'error': f'Failed to upload results. Status code: {upload_response.status_code}',
                    'response': upload_response.text
                }
    except Exception as e:
        return {'error': f'Error uploading results: {str(e)}'}

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Welcome to the server!',
        'endpoints': {
            '/': 'This help message',
            '/process': 'GET endpoint to trigger image processing',
            '/upload': 'POST endpoint for file uploads',
            '/status': 'GET endpoint to check server status'
        }
    })

@app.route('/process', methods=['POST'])
def process_post():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Respond immediately
        response = {
            'message': 'File uploaded successfully, processing started.',
            'filename': filename,
            'size': os.path.getsize(file_path)
        }
        # Start processing in background
        Thread(target=process_image, args=(file_path,)).start()
        return jsonify(response)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'size': os.path.getsize(file_path)
        })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'files': os.listdir(app.config['UPLOAD_FOLDER'])
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 