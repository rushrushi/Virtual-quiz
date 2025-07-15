import cv2
import numpy as np
import mediapipe as mp
import time
import pygame
import sys

# Init pygame mixer for sound
pygame.mixer.init()
sound_correct = pygame.mixer.Sound(r"D:\Rushi Works\Projects\CV\click_button\virtual_quiz_game\correct.mp3")
sound_wrong = pygame.mixer.Sound(r"D:\Rushi Works\Projects\CV\click_button\virtual_quiz_game\wrong.mp3")

# Background Music
pygame.mixer.music.load(r"D:\Rushi Works\Projects\CV\click_button\virtual_quiz_game\background_music.mp3")
pygame.mixer.music.set_volume(0.3)
pygame.mixer.music.play(-1, 0.0)

# Timer Settings
QUESTION_TIME_LIMIT = 10
question_start_time = time.time()

# MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Questions
questions = [
    {"question": "What is the capital of France?", "options": ["Paris", "London", "Rome", "Berlin"], "answer": "Paris"},
    {"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Venus", "Mars", "Jupiter"], "answer": "Mars"},
    {"question": "Who wrote 'Hamlet'?", "options": ["Shakespeare", "Homer", "Dickens", "Tolstoy"], "answer": "Shakespeare"},
    {"question": "What is the largest mammal?", "options": ["Elephant", "Blue Whale", "Shark", "Giraffe"], "answer": "Blue Whale"},
    {"question": "How many continents are there?", "options": ["5", "6", "7", "8"], "answer": "7"}
]

# Game state
current_q = 0
score = 0
selected_option = None
feedback = ""
show_feedback = False
feedback_time = 0
feedback_duration = 2

option_boxes = []
was_inside_box = [False] * 4
option_status = [None] * 4

# Webcam
cap = cv2.VideoCapture(0)
cv2.namedWindow("Gesture Quiz Game", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Gesture Quiz Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

def draw_text_with_stroke(img, text, position, font, scale, color, stroke_color, thickness):
    x, y = position
    cv2.putText(img, text, (x, y), font, scale, stroke_color, thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

def draw_question(img, q_data):
    global option_boxes, option_status
    h, w, _ = img.shape
    option_boxes.clear()

    # Adjust question box area
    question_box_height = 120
    option_height = 70  # Increased option height
    padding = 30

    cv2.rectangle(img, (padding, 20), (w - padding, question_box_height), (0, 0, 0), -1)
    draw_text_with_stroke(img, f"Q{current_q+1}: {q_data['question']}", (padding + 10, question_box_height - 20),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), (0, 0, 0), 2)

    # Adjust the options to fit better on the screen and position them in a grid
    # A is top-left, B is top-right, C is bottom-left, D is bottom-right
    option_positions = [
        (padding, question_box_height + padding),  # A
        (w - padding - 200, question_box_height + padding),  # B
        (padding, h - padding - option_height - 60),  # C
        (w - padding - 200, h - padding - option_height - 60)  # D
    ]
    
    for i, (x, y) in enumerate(option_positions):
        x1, y1 = x, y
        x2, y2 = x1 + 200, y1 + option_height  # Increased box width and height
        option_boxes.append((x1, y1, x2, y2))

        color = (60, 180, 255)
        if option_status[i] == "correct":
            color = (0, 200, 0)
        elif option_status[i] == "wrong":
            color = (0, 0, 255)

        # Border for option boxes
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), 2)  # Border
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)  # Background color of the option box
        
        # Adding labels A), B), C), D)
        label = chr(65 + i)  # ASCII value for 'A' is 65
        cv2.putText(img, f"{label}) {q_data['options'][i]}", (x1 + 20, y1 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

def draw_feedback(img):
    if show_feedback and time.time() - feedback_time < feedback_duration:
        draw_text_with_stroke(img, feedback, (180, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), (0, 0, 0), 3)
    elif show_feedback:
        next_question()

def draw_timer(img):
    remaining = max(0, QUESTION_TIME_LIMIT - int(time.time() - question_start_time))
    text = f"Time Left: {remaining}s"
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    text_x = img.shape[1] - text_size[0] - 30
    text_y = img.shape[0] - 30

    # Change color to red when less than or equal to 5 seconds
    timer_color = (0, 0, 255) if remaining <= 5 else (255, 255, 255)
    
    draw_text_with_stroke(img, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                          timer_color, (0, 0, 0), 2)
    return remaining

def next_question():
    global current_q, selected_option, show_feedback, feedback, feedback_time, option_status, question_start_time
    selected_option = None
    show_feedback = False
    feedback = ""
    feedback_time = 0
    option_status = [None] * 4
    question_start_time = time.time()
    current_q += 1

def show_final_score(img):
    draw_text_with_stroke(img, f"Game Over! Your Score: {score}/{len(questions)}", (100, 250),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), (0, 0, 0), 3)  # Reduced font size

    retry_btn = (150, 330, 350, 400)
    exit_btn = (400, 330, 600, 400)

    cv2.rectangle(img, (retry_btn[0], retry_btn[1]), (retry_btn[2], retry_btn[3]), (60, 180, 255), -1)
    cv2.putText(img, "Retry", (retry_btn[0]+50, retry_btn[1]+45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    cv2.rectangle(img, (exit_btn[0], exit_btn[1]), (exit_btn[2], exit_btn[3]), (255, 80, 80), -1)
    cv2.putText(img, "Exit", (exit_btn[0]+60, exit_btn[1]+45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    if index_finger_tip:
        rx1, ry1, rx2, ry2 = retry_btn
        ex1, ey1, ex2, ey2 = exit_btn

        if rx1 <= index_finger_tip[0] <= rx2 and ry1 <= index_finger_tip[1] <= ry2:
            reset_game()
        elif ex1 <= index_finger_tip[0] <= ex2 and ey1 <= index_finger_tip[1] <= ey2:
            pygame.mixer.music.stop()
            cap.release()
            cv2.destroyAllWindows()
            sys.exit()

def reset_game():
    global current_q, score, question_start_time
    current_q = 0
    score = 0
    question_start_time = time.time()

# Main Loop
while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    # Smoothing and sharpening
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    img = cv2.filter2D(blurred, -1, kernel)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    index_finger_tip = None
    h, w, _ = img.shape

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            lm = hand_landmarks.landmark[8]
            cx, cy = int(lm.x * w), int(lm.y * h)
            index_finger_tip = (cx, cy)
            cv2.circle(img, index_finger_tip, 10, (255, 0, 0), cv2.FILLED)

    if current_q < len(questions):
        draw_question(img, questions[current_q])
        time_left = draw_timer(img)

        if time_left == 0 and not show_feedback:
            feedback = "Time's Up!"
            sound_wrong.play()
            show_feedback = True
            feedback_time = time.time()

        if index_finger_tip:
            for i, (x1, y1, x2, y2) in enumerate(option_boxes):
                inside = x1 <= index_finger_tip[0] <= x2 and y1 <= index_finger_tip[1] <= y2

                if inside and not was_inside_box[i] and not show_feedback:
                    selected_option = questions[current_q]['options'][i]
                    correct = selected_option == questions[current_q]['answer']
                    if correct:
                        feedback = "Correct!"
                        sound_correct.play()
                        score += 1
                        option_status[i] = "correct"
                    else:
                        feedback = "Try Again!"
                        sound_wrong.play()
                        option_status[i] = "wrong"
                    show_feedback = True
                    feedback_time = time.time()
                    was_inside_box[i] = True
                elif not inside:
                    was_inside_box[i] = False

        draw_feedback(img)
    else:
        show_final_score(img)

    cv2.imshow("Gesture Quiz Game", img)
    if cv2.waitKey(10) == 27:
        break

pygame.mixer.music.stop()
cap.release()
cv2.destroyAllWindows()
