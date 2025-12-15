import cv2
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import json
import os
# --- Imports ---
import cv2
import easyocr

# Force fixed model directory (prevents Windows lock)
os.environ["EASYOCR_MODULE_PATH"] = r"G:\wepractice13oct\library\lib\easyocr_models"
# ✅ CREATE READER GLOBALLY
reader = easyocr.Reader(
    ['en'],
    gpu=False,
    verbose=False,
    quantize=True
)

import numpy as np
from collections import defaultdict
import pprint
def convert_to_bw(input_path, output_path,query):
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"[ERROR] Input file does not exist: {input_path}")
        sys.exit(1)
    
    print(f"[INFO] Reading image from: {input_path}")
    
    # Read the image
    image = cv2.imread(input_path)
    if image is None:
        print(f"[ERROR] Failed to read image. Is it a valid image file?")
        sys.exit(1)
    
    print(f"[INFO] Converting image to grayscale...")
    
    # Convert to grayscale
        

    


    # --- Rotate image and return rotation matrix ---
    def rotate_image(img, angle):
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return rotated, M

    # --- Rotate coordinates using rotation matrix ---
    def rotate_coords(coords, M):
        coords = np.array(coords)
        ones = np.ones((coords.shape[0], 1))
        points_ones = np.hstack([coords, ones])
        rotated = M.dot(points_ones.T).T
        return [tuple(pt) for pt in rotated]

    # --- Compute distance between two boxes using top-left corner ---
    def box_distance(box1, box2):
        return np.linalg.norm(np.array(box1[0]) - np.array(box2[0]))

    # --- Track unique boxes across all angles ---
    def track_unique_boxes_all_angles(image_path):
        img0 = cv2.imread(image_path)
        unique_boxes = {}
        box_counter = 1
        angle_mean_conf = {}

        for angle in [0, 90, 180, 270]:
            rotated_img, M = rotate_image(img0, angle)
            results = reader.readtext(rotated_img)

            if results:
                mean_conf = np.mean([r[2] for r in results])
                angle_mean_conf[angle] = mean_conf
            else:
                angle_mean_conf[angle] = 0.0

            for bbox, text, conf in results:
                matched_box = None
                # check if any existing box matches current box (rotated back)
                for bkey, bval in unique_boxes.items():
                    for a, coords_rot in bval['rotated_coords'].items():
                        # rotate old box from angle a to current angle
                        delta_angle = angle - a
                        h, w = img0.shape[:2]
                        M_delta = cv2.getRotationMatrix2D((w/2, h/2), delta_angle, 1.0)
                        coords_mapped = rotate_coords(coords_rot, M_delta)
                        dist = box_distance(coords_mapped, bbox)
                        if dist < 10:  # threshold
                            matched_box = bkey
                            break
                    if matched_box:
                        break

                if matched_box is None:
                    key = f"b{box_counter}"
                    unique_boxes[key] = {
                        'coords': bbox,
                        'texts': {angle: text},
                        'confs': {angle: conf},
                        'rotated_coords': {angle: rotate_coords(bbox, M)}
                    }
                    box_counter += 1
                else:
                    unique_boxes[matched_box]['texts'][angle] = text
                    unique_boxes[matched_box]['confs'][angle] = conf
                    unique_boxes[matched_box]['rotated_coords'][angle] = rotate_coords(bbox, M)

        return unique_boxes, angle_mean_conf, img0

    # --- Draw all boxes on best-angle image ---
    def draw_boxes_best_angle(unique_boxes, img0, best_angle):
        img_best, M_best = rotate_image(img0, best_angle)
        for bkey, bval in unique_boxes.items():
            # pick any existing rotated coords
            angle_from = next(iter(bval['rotated_coords']))
            coords_from = np.array(bval['rotated_coords'][angle_from])
            delta_angle = best_angle - angle_from
            h, w = img0.shape[:2]
            M_delta = cv2.getRotationMatrix2D((w/2, h/2), delta_angle, 1.0)
            coords_mapped = rotate_coords(coords_from, M_delta)
            pts = np.array(coords_mapped, np.int32)

            cv2.polylines(img_best, [pts], True, (0,0,255), 2)
            x, y = int(pts[0][0]), int(pts[0][1]) - 5
            cv2.putText(img_best, bkey, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2, cv2.LINE_AA)
        return img_best

    # ------------------ RUN ------------------
    image_path = input_path
    unique_boxes, angle_mean_conf, img0 = track_unique_boxes_all_angles(image_path)
    def serialize_unique_boxes(unique_boxes):
        mybooks = []

        for box_id, box_data in unique_boxes.items():
            book = {
                "boxId": box_id,
                "texts": box_data["texts"],          # angle -> text
                "confs": box_data["confs"],          # angle -> confidence
                "coords": [
                    {"x": int(pt[0]), "y": int(pt[1])}
                    for pt in box_data["coords"]
                ]
            }
            mybooks.append(book)

        return mybooks
    bookslist = serialize_unique_boxes(unique_boxes)

    # Compute best angle by mean confidence
    best_angle = max(angle_mean_conf.items(), key=lambda x: x[1])[0]
    #print(f"Best angle = {best_angle}°, mean_conf={angle_mean_conf[best_angle]:.3f}\n")

    # Draw all boxes on best-angle image
    img_best = draw_boxes_best_angle(unique_boxes, img0, best_angle)

    # Display image
    # ===============================
    # FUZZY ENGLISH TEXT MATCHING
    # ===============================

    def edit_distance(a, b):
        a, b = a.lower(), b.lower()
        dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]

        for i in range(len(a) + 1):
            dp[i][0] = i
        for j in range(len(b) + 1):
            dp[0][j] = j

        for i in range(1, len(a) + 1):
            for j in range(1, len(b) + 1):
                cost = 0 if a[i-1] == b[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost
                )
        return dp[-1][-1]


    def is_similar_english(text, target="english", max_dist=2):
        if not text.isascii():
            return False
        if len(text) < 4:
            return False
        return edit_distance(text, target) <= max_dist


    # ===============================
    # DRAW MATCHED BOXES ONLY
    # ===============================

    search_word = query  # word to search for
    img_match = img0.copy()
    matched_boxes = {}

    for box_id, box_data in unique_boxes.items():
        matched_text = None

        # check ALL detected texts (all angles)
        for text in box_data['texts'].values():
            if is_similar_english(text, search_word):
                matched_text = text  # ORIGINAL OCR TEXT
                break

        if matched_text is not None:
            pts = np.array(box_data['coords'], dtype=np.int32)

            # draw box
            cv2.polylines(img_match, [pts], True, (0, 255, 0), 3)

            # draw original OCR text
            x, y = pts[0][0], pts[0][1] - 8
            cv2.putText(
                img_match,
                matched_text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

            matched_boxes[box_id] = box_data

    # ===============================
    # CASE 2: NO MATCH → RED WARNING CENTERED
    # ===============================

    if len(matched_boxes) == 0:
        h, w = img_match.shape[:2]
        warning_text = "No matching English word found"

        # Get text size
        (text_width, text_height), _ = cv2.getTextSize(
            warning_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,   # font scale
            3      # thickness
        )

        # Center horizontally, position near bottom
        x = (w - text_width) // 2
        y = h - 30

        cv2.putText(
            img_match,
            warning_text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,           # font scale
            (0, 0, 255),   # red
            3,             # thickness for bold
            cv2.LINE_AA
        )

    # ===============================
    # SHOW RESULT
    # ===============================




    #img_best is the final image with boxes drawn
    #img_match is the search word matched image
    gray_image =img_match
#our code ends here output is gray-image ******************************************************************************************
#*********************************
#*************
    # Save the result
    cv2.imwrite(output_path, gray_image)
    
    if os.path.exists(output_path):
        print(f"[SUCCESS] Processed image saved to: {output_path}")
    else:
        print(f"[ERROR] Failed to save output image: {output_path}")
        
    print("===JSON_START===")
    print(json.dumps(bookslist, ensure_ascii=False))
    print("===JSON_END===")




if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python process_book.py <input_path> <output_path>")
        sys.exit(1)

    # Input arguments from command line


    input_img = sys.argv[1]
    output_img = sys.argv[2]


    query = sys.argv[3]

# Example processing: convert to grayscale

    print(f"Processed text for: {query}")   # returned to Spring

    print("vamshi")

    convert_to_bw(input_img, output_img,query)
