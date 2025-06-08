import json
import os
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

# Function to check for matching objects
def check_matching_objects(old_json, new_json, save_dir, iou_threshold=0.5):
    # Load JSON data
    with open(old_json, 'r') as f1, open(new_json, 'r') as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    # Check for matches and unmatched objects
    matches = []
    unmatched_old = data1.copy()
    unmatched_new = data2.copy()

    for obj1 in data1:
        for obj2 in data2:
            iou = calculate_iou(obj1['bounding_box'], obj2['bounding_box'])
            if iou > iou_threshold:
                matches.append({'old_object_id': obj1['object_id'], 'new_object_id': obj2['object_id'], 'iou': iou})
                if obj1 in unmatched_old:
                    unmatched_old.remove(obj1)
                if obj2 in unmatched_new:
                    unmatched_new.remove(obj2)

    # Prepare unmatched objects with specific key names
    unmatched_old_formatted = [{'old_object_id': obj['object_id'], 'bounding_box': obj['bounding_box']} for obj in unmatched_old] # object_id -> id in old.json
    unmatched_new_formatted = [{'new_object_id': obj['object_id'], 'bounding_box': obj['bounding_box']} for obj in unmatched_new] # object_id -> id in new.json

    # Save matches and unmatched objects to JSON files
    with open(os.path.join(save_dir, 'match.json'), 'w') as match_file:
        json.dump(matches, match_file, indent=4)

    with open(os.path.join(save_dir,'delete.json'), 'w') as delete_file:
        json.dump(unmatched_old_formatted, delete_file, indent=4)

    with open(os.path.join(save_dir, 'add.json'), 'w') as add_file:
        json.dump(unmatched_new_formatted, add_file, indent=4)

    return matches

# Example usage
if __name__ == "__main__":
    old_json = 'result1.json'
    new_json = 'result2.json'
    matches = check_matching_objects(old_json, new_json, './')
    print("Matching objects saved in match.json")
    print("Unmatched objects in old JSON saved in delete.json")
    print("Unmatched objects in new JSON saved in add.json")
