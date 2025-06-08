import requests
import os
import shutil
import json
from object_detection import detect_objects
from change_detection import check_matching_objects


if __name__ == "__main__":
    save_dir = './'
    result_dir = './result'
    json_dir = os.path.join(result_dir, 'json')
    os.makedirs(json_dir, exist_ok=True)
   
    api_url = 'https://example.com/api/get_image'
    upload_url = 'https://052f-140-112-25-5.ngrok-free.app/upload/zip'  # Updated upload URL
    
    # Define image filename
    img_filename = 'fruit.png'
    img_path = os.path.join(save_dir, img_filename)
    response = requests.get(api_url)
    
    # Check for success
    if response.status_code == 200:
        with open(img_path, 'wb') as f:
            f.write(response.content)
        print(f'Image successfully downloaded and saved to {img_path}')
    else:
        print(f'Failed to download image. Status code: {response.status_code}')
    
    # Generate JSON path for detection results
    json_path = os.path.join(json_dir, 'new.json')
    old_json_path = os.path.join(json_dir, 'old.json')
    os.rename(json_path, old_json_path)
    print(f'Renamed {json_path} to {old_json_path}')
    detect_objects(img_path=img_path, json_path=json_path, save_dir=result_dir)
    check_matching_objects(old_json=old_json_path, new_json=json_path, save_dir=json_dir)

    # Create a zip file of the result directory
    zip_filename = 'data.zip'  # Updated to match curl command
    shutil.make_archive('data', 'zip', result_dir)
    print(f'Created zip file: {zip_filename}')

    # Send the zip file back to the backend
    try:
        print("posting")
        with open(zip_filename, 'rb') as f:
            files = {
                'file': (zip_filename, f, 'application/zip')
            }
            upload_response = requests.post(
                upload_url,
                files=files
            )
            
            if upload_response.status_code == 200:
                print('Results successfully uploaded to backend')
                print(f'Response: {upload_response.text}')
            else:
                print(f'Failed to upload results. Status code: {upload_response.status_code}')
                print(f'Response: {upload_response.text}')
    except Exception as e:
        print(f'Error uploading results: {str(e)}')
    



