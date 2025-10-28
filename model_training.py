import os
from imutils import paths
import face_recognition
import pickle
import cv2

print("\n" + "="*50)
print("AI HOUSE ASSISTANT - Model Training")
print("="*50)
print("[INFO] Starting face encoding process...")
print("="*50 + "\n")

# Get all image paths from dataset folder
imagePaths = list(paths.list_images("dataset"))

if len(imagePaths) == 0:
    print("[ERROR] No images found in 'dataset' folder!")
    print("[INFO] Please run 'capture_photos.py' first to add training images")
    exit()

print(f"[INFO] Found {len(imagePaths)} images to process")

# Initialize lists to store encodings and names
knownEncodings = []
knownNames = []

# Process each image
for (i, imagePath) in enumerate(imagePaths):
    print(f"[INFO] Processing image {i + 1}/{len(imagePaths)}: {os.path.basename(imagePath)}")
    
    # Extract person name from folder structure (dataset/name/image.jpg)
    name = imagePath.split(os.path.sep)[-2]
    
    # Load image and convert to RGB
    image = cv2.imread(imagePath)
    if image is None:
        print(f"[WARNING] Could not read image: {imagePath}")
        continue
        
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect faces and generate encodings
    boxes = face_recognition.face_locations(rgb, model="hog")
    encodings = face_recognition.face_encodings(rgb, boxes)
    
    if len(encodings) == 0:
        print(f"[WARNING] No face detected in: {os.path.basename(imagePath)}")
        continue
    
    # Add encodings to our lists
    for encoding in encodings:
        knownEncodings.append(encoding)
        knownNames.append(name)
        print(f"[INFO] ✓ Encoded face for: {name}")

if len(knownEncodings) == 0:
    print("\n[ERROR] No faces were successfully encoded!")
    print("[INFO] Please check that:")
    print("  - Images contain clear, visible faces")
    print("  - Images are in dataset/[person_name]/ folders")
    print("  - Images are in .jpg, .jpeg, or .png format")
    exit()

# Save encodings to file
print("\n[INFO] Serializing encodings to 'encodings.pickle'...")
data = {"encodings": knownEncodings, "names": knownNames}

try:
    with open("encodings.pickle", "wb") as f:
        f.write(pickle.dumps(data))
    print("[INFO] ✓ Successfully saved encodings!")
except Exception as e:
    print(f"[ERROR] Failed to save encodings: {e}")
    exit()

# Summary
unique_names = set(knownNames)
print("\n" + "="*50)
print("TRAINING COMPLETE")
print("="*50)
print(f"Total faces encoded: {len(knownEncodings)}")
print(f"Number of people: {len(unique_names)}")
print(f"People in database: {', '.join(sorted(unique_names))}")
print(f"Encodings saved to: encodings.pickle")
print("\nNext step: Run 'python main.py' to start the system")
print("="*50 + "\n")