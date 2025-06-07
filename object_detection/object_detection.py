import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import cv2
import numpy as np
import json

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

    # Function to calculate IoU
def calculate_iou(box1, box2):
    x1, y1, x2, y2 = box1
    x1_p, y1_p, x2_p, y2_p = box2

    # Calculate the intersection coordinates
    xi1 = max(x1, x1_p)
    yi1 = max(y1, y1_p)
    xi2 = min(x2, x2_p)
    yi2 = min(y2, y2_p)

    # Calculate the area of intersection
    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    intersection = inter_width * inter_height

    # Calculate the area of both bounding boxes
    box1_area = (x2 - x1) * (y2 - y1)
    box2_area = (x2_p - x1_p) * (y2_p - y1_p)

    # Calculate the union area
    union = box1_area + box2_area - intersection

    # Calculate IoU
    iou = intersection / union if union != 0 else 0
    return iou

def detect_objects(img_path, json_path, save_dir, threshold=0.4):
    # Load the model and processor
    model_id = "IDEA-Research/grounding-dino-base"
    device = "cuda"
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

    # Load the image using OpenCV
    image = cv2.imread(img_path)

    # Convert BGR to RGB for correct color representation
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Define text labels
    text_labels = [["drinks", "food", "fruit","vegetable", "meat", "grocery"]]

    # Prepare inputs
    inputs = processor(images=image_rgb, text=text_labels, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)

    # Post-process results
    results = processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        box_threshold=threshold,
        text_threshold=0.3,
        target_sizes=[(image.shape[0], image.shape[1])]  # Use height and width from OpenCV
    )

    result = results[0]
    for box, score, labels in zip(result["boxes"], result["scores"], result["labels"]):
        box = [round(x, 2) for x in box.tolist()]
        print(f"Detected {labels} with confidence {round(score.item(), 3)} at location {box}")

    # Assuming result['boxes'] and result['scores'] are tensors
    boxes = result['boxes'].detach().cpu().numpy()  # Move to CPU and convert to NumPy
    scores = result['scores'].detach().cpu().numpy()  # Move to CPU and convert to NumPy


    # Initialize a list to store object data
    object_data = []

    # Draw bounding boxes and crop objects using OpenCV
    object_id = 0
    for box, score in zip(boxes, scores):
        if score > threshold:  # Confidence threshold
            x1, y1, x2, y2 = map(int, box)
            
            # Crop the object from the image
            cropped_object = image[y1:y2, x1:x2]
            
            # Save the cropped object as a new image
            object_image_path = f'object_{object_id}.png'
            cv2.imwrite(object_image_path, cropped_object)
            
            # Log the object data
            object_data.append({
                'object_id': object_id,
                'bounding_box': [x1, y1, x2, y2],
                'image_path': object_image_path
            })
            
            object_id += 1

    # Remove redundant boxes based on IoU before writing to JSON
    filtered_object_data = []
    for i, obj1 in enumerate(object_data):
        is_redundant = False
        for j, obj2 in enumerate(object_data):
            if i > j:
                iou = calculate_iou(obj1['bounding_box'], obj2['bounding_box'])
                if iou > 0.7:
                    is_redundant = True
                    break
        if not is_redundant:
            filtered_object_data.append(obj1)

    # Write the filtered object data to a JSON file
    with open(json_path, 'w') as json_file:
        json.dump(filtered_object_data, json_file, indent=4)


if __name__ == "__main__":
    # Example usage
    detect_objects(img_path='fruit.png', json_path='result.json', save_dir='./')
    