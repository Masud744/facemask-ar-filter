import cv2
import mediapipe as mp
import numpy as np
import math

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()

# Start webcam
cap = cv2.VideoCapture(0)

# Load mask image and convert to BGRA (add alpha channel)
mask_img = cv2.imread("computer_vision/filters/spiderman.png")
mask_img = cv2.cvtColor(mask_img, cv2.COLOR_BGR2BGRA)


# Smart background removal:
# Removes only the white background connected to image borders
# Keeps internal white regions (e.g., eye areas of the mask)
def remove_background_smart(img):
    # Create a copy of the image
    result = img.copy()
    
    # Detect white pixels
    white_mask = (
        (img[:, :, 0] > 240) &
        (img[:, :, 1] > 240) &
        (img[:, :, 2] > 240)
    ).astype(np.uint8) * 255
    
    # Flood fill from the four corners to find border-connected white regions
    h, w = white_mask.shape
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    
    temp = white_mask.copy()
    corners = [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]
    
    for r, c in corners:
        if temp[r, c] == 255:
            cv2.floodFill(temp, flood_mask, (c, r), 128)
    
    # Pixels marked as 128 are border-connected white (background)
    border_white = (temp == 128)
    
    # Make those pixels transparent
    result[border_white, 3] = 0
    
    return result


# Apply smart background removal to mask image
mask_img = remove_background_smart(mask_img)


# Main loop for video processing
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to RGB for MediaPipe processing
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    # If face landmarks detected
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            h, w, _ = frame.shape

            # Get key landmarks: left eye, right eye, nose
            left_eye = face_landmarks.landmark[33]
            right_eye = face_landmarks.landmark[263]
            nose = face_landmarks.landmark[1]

            # Convert normalized coordinates to pixel coordinates
            x_left = int(left_eye.x * w)
            y_left = int(left_eye.y * h)
            x_right = int(right_eye.x * w)
            y_right = int(right_eye.y * h)
            nose_x = int(nose.x * w)
            nose_y = int(nose.y * h)

            # Estimate mask size based on distance between eyes
            eye_distance = abs(x_right - x_left)
            mask_width = int(eye_distance * 2.5)
            mask_height = int(mask_width * 1.2)

            # Resize mask
            resized_mask = cv2.resize(mask_img, (mask_width, mask_height))

            # Calculate face rotation angle
            angle = math.degrees(math.atan2(y_right - y_left, x_right - x_left))

            # Rotate mask to match face orientation
            center = (mask_width // 2, mask_height // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1)
            rotated_mask = cv2.warpAffine(resized_mask, M, (mask_width, mask_height))

            # Position mask centered around nose
            x = int(nose_x - mask_width / 2)
            y = int(nose_y - mask_height / 2)

            # Overlay mask if inside frame boundaries
            if x > 0 and y > 0 and x + mask_width < w and y + mask_height < h:
                mask_rgb = rotated_mask[:, :, :3]
                mask_alpha = rotated_mask[:, :, 3] / 255.0

                # Alpha blending
                for c in range(3):
                    frame[y:y+mask_height, x:x+mask_width, c] = \
                        mask_alpha * mask_rgb[:, :, c] + \
                        (1 - mask_alpha) * frame[y:y+mask_height, x:x+mask_width, c]

    # Show output frame
    cv2.imshow("Spider-Man Filter", frame)

    # Press ESC to exit
    if cv2.waitKey(1) & 0xFF == 27:
        break


# Release resources
cap.release()
cv2.destroyAllWindows()