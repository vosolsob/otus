import picamera2
import RPi.GPIO as GPIO
import threading
import keyboard  # for capturing key presses

# Constants
Z_UP_KEY = 'q'
Z_DOWN_KEY = 'a'

class StepperMotorController:
    def __init__(self, step_pin, dir_pin, limit_switch_pin):
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.limit_switch_pin = limit_switch_pin
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.limit_switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def move_up(self, steps):
        GPIO.output(self.dir_pin, GPIO.HIGH)  # Set direction up
        for _ in range(steps):
            if GPIO.input(self.limit_switch_pin) == GPIO.LOW:
                break  # Stop if the limit switch is triggered
            GPIO.output(self.step_pin, GPIO.HIGH)
            GPIO.output(self.step_pin, GPIO.LOW)

    def move_down(self, steps):
        GPIO.output(self.dir_pin, GPIO.LOW)  # Set direction down
        for _ in range(steps):
            if GPIO.input(self.limit_switch_pin) == GPIO.LOW:
                break  # Stop if the limit switch is triggered
            GPIO.output(self.step_pin, GPIO.HIGH)
            GPIO.output(self.step_pin, GPIO.LOW)

class RaspberryCameraController:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.camera.configure(self.camera.create_video_configuration(main={"size": (1920, 1080)}))

    def take_picture(self, filename):
        self.camera.start()
        self.camera.capture(filename)
        self.camera.stop()

class KeyboardController:
    def __init__(self, stepper_motor):
        self.stepper_motor = stepper_motor

    def listen(self):
        while True:
            if keyboard.is_pressed(Z_UP_KEY):
                self.stepper_motor.move_up(50)  # Example step count
            elif keyboard.is_pressed(Z_DOWN_KEY):
                self.stepper_motor.move_down(50)  # Example step count

if __name__ == "__main__":
    stepper = StepperMotorController(step_pin=17, dir_pin=27, limit_switch_pin=22)
    camera_controller = RaspberryCameraController()
    keyboard_controller = KeyboardController(stepper)

    # Start keyboard listening in a separate thread
    listener_thread = threading.Thread(target=keyboard_controller.listen)
    listener_thread.start()