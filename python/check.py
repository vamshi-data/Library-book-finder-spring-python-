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
img_path = sys.argv[1]
json_path = sys.argv[2]
out_path = sys.argv[3]
search_word = sys.argv[4]

img_match = cv2.imread(img_path)

with open(json_path, "r", encoding="utf-8") as f:
    myjson = json.load(f)  # it's already a list


def edit_distance(a, b):
    a, b = a.lower(), b.lower()
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1): dp[i][0] = i
    for j in range(len(b)+1): dp[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j]+1,
                dp[i][j-1]+1,
                dp[i-1][j-1]+cost
            )
    return dp[-1][-1]

def is_similar_english(text, target, max_dist=2):
    return text.isascii() and len(text) >= 4 and \
           edit_distance(text, target) <= max_dist

matched_boxes = {}

for box in myjson:
    matched_text = None

    for text in box["texts"].values():
        if is_similar_english(text, search_word):
            matched_text = text
            break

    if matched_text:
        pts = np.array(
            [[p["x"], p["y"]] for p in box["coords"]],
            dtype=np.int32
        )

        cv2.polylines(img_match, [pts], True, (0,255,0), 3)
        x, y = pts[0][0], pts[0][1] - 8
        cv2.putText(img_match, matched_text, (x,y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        matched_boxes[box["boxId"]] = box

if not matched_boxes:
    h, w = img_match.shape[:2]
    cv2.putText(
        img_match,
        "No matching English word found",
        ((w-600)//2, h-30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2, (0,0,255), 3
    )

cv2.imwrite(out_path, img_match)
