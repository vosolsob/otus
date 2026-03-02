import tkinter as tk
from picamera2 import Picamera2
from stepper_motor_controller import StepperMotorController

# Define keyboard commands
KEY_COMMANDS = {
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "z_plus": "q",
    "z_minus": "a",
    "roi_start": "b",
    "roi_end": "n",
    "confirm_roi": " ",
    "reset_roi": "r"
}

class CameraApp:
    def __init__(self, root):
        self.picamera = Picamera2()
        self.motor_controller = StepperMotorController()
        self.roi_points = []
        self.create_widgets(root)
        self.setup_keyboard_bindings(root)

    def create_widgets(self, root):
        self.label = tk.Label(root, text="Camera Control with Stepper Motors")
        self.label.pack()
        self.start_button = tk.Button(root, text="Start Camera", command=self.start_camera)
        self.start_button.pack()

    def setup_keyboard_bindings(self, root):
        root.bind("<KeyPress>", self.handle_keypress)

    def handle_keypress(self, event):
        if event.keysym == KEY_COMMANDS["left"]:
            self.motor_controller.move_x(-1)
        elif event.keysym == KEY_COMMANDS["right"]:
            self.motor_controller.move_x(1)
        elif event.keysym == KEY_COMMANDS["up"]:
            self.motor_controller.move_y(1)
        elif event.keysym == KEY_COMMANDS["down"]:
            self.motor_controller.move_y(-1)
        elif event.keysym == KEY_COMMANDS["z_plus"]:
            self.motor_controller.move_z(1)
        elif event.keysym == KEY_COMMANDS["z_minus"]:
            self.motor_controller.move_z(-1)
        elif event.keysym == KEY_COMMANDS["roi_start"]:
            self.roi_points.append((self.motor_controller.current_x, self.motor_controller.current_y))
        elif event.keysym == KEY_COMMANDS["roi_end"]:
            self.roi_points.append((self.motor_controller.current_x, self.motor_controller.current_y))
        elif event.keysym == KEY_COMMANDS["confirm_roi"]:
            self.confirm_roi()
        elif event.keysym == KEY_COMMANDS["reset_roi"]:
            self.reset_roi()

    def confirm_roi(self):
        print(f"ROI Points: {self.roi_points}")

    def reset_roi(self):
        self.roi_points = []
        print("ROI reset.")

    def start_camera(self):
        self.picamera.start_preview()
        print("Camera started.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()