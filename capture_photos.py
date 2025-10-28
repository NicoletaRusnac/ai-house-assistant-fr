import cv2
import os
from datetime import datetime
from picamera2 import Picamera2
import time

# Configuration - CHANGE THIS to the person's name
PERSON_NAME = "nicoleta"  # Edit this for each person you want to add

def create_folder():
    """Create a folder for the person if it doesn't exist"""
    folder_path = f"dataset/{PERSON_NAME}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"[INFO] Created folder: {folder_path}")
    else:
        print(f"[INFO] Using existing folder: {folder_path}")
    return folder_path

def capture_photos():
    """Capture photos using Raspberry Pi Camera Module 3"""
    folder_path = create_folder()
    
    # Initialize camera
    print("[INFO] Initializing Raspberry Pi Camera Module 3...")
    try:
        picam2 = Picamera2()
        picam2.configure(picam2.create_preview_configuration(
            main={"format": 'XRGB8888', "size": (640, 480)}
        ))
        picam2.start()
        time.sleep(2)  # Camera warm-up time
        print("[INFO] Camera ready!")
    except Exception as e:
        print(f"[ERROR] Failed to initialize camera: {e}")
        return
    
    print("\n" + "="*50)
    print("PHOTO CAPTURE INSTRUCTIONS")
    print("="*50)
    print("- Press SPACE BAR to capture a photo")
    print("- Press Q to quit and finish")
    print(f"- Photos will be saved to: {folder_path}")
    print("- Recommended: Capture at least 10 photos per person")
    print("- Tip: Take photos from different angles and lighting")
    print("="*50 + "\n")
    
    photo_count = 0
    
    try:
        while True:
            # Capture frame from camera
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Add instructions overlay on the frame
            cv2.putText(frame, f"Person: {PERSON_NAME}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Photos captured: {photo_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "SPACE = Capture | Q = Quit", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow('Capture Photos - AI House Assistant', frame)
            
            # Wait for key press
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' '):  # Space bar - capture photo
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{PERSON_NAME}_{timestamp}.jpg"
                filepath = os.path.join(folder_path, filename)
                
                # Save photo
                cv2.imwrite(filepath, frame)
                photo_count += 1
                print(f"[INFO] ✓ Saved: {filename} (Total: {photo_count})")
                
                # Visual feedback - flash the screen
                flash_frame = frame.copy()
                cv2.rectangle(flash_frame, (0, 0), (640, 480), (255, 255, 255), -1)
                cv2.imshow('Capture Photos - AI House Assistant', flash_frame)
                cv2.waitKey(100)
                
            elif key == ord('q'):  # Q key - quit
                print("\n[INFO] Quitting capture mode...")
                break
    
    except KeyboardInterrupt:
        print("\n[INFO] Capture interrupted by user")
    
    finally:
        # Cleanup
        cv2.destroyAllWindows()
        picam2.stop()
        
        print("\n" + "="*50)
        print("CAPTURE COMPLETE")
        print("="*50)
        print(f"Total photos captured: {photo_count}")
        print(f"Photos saved in: {folder_path}")
        print("\nNext steps:")
        print("1. Review photos in the dataset folder")
        print("2. Repeat this process for other people")
        print("3. Run 'python model_training.py' to train the model")
        print("="*50 + "\n")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("AI HOUSE ASSISTANT - Photo Capture Utility")
    print("="*50)
    print(f"Current person: {PERSON_NAME}")
    print("Edit PERSON_NAME in capture_photos.py to change")
    print("="*50 + "\n")
    
    capture_photos()
    