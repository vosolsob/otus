import keyboard

class MotorControl:
    def __init__(self):
        self.position_z = 0

    def move_up(self):
        self.position_z += 1
        print(f'Moved up to position {self.position_z}')

    def move_down(self):
        self.position_z -= 1
        print(f'Moved down to position {self.position_z}')

    def listen_for_keys(self):
        keyboard.add_hotkey('q', self.move_up)
        keyboard.add_hotkey('a', self.move_down)
        print('Listening for keyboard input...')
        keyboard.wait()

if __name__ == '__main__':
    motor_control = MotorControl()
    motor_control.listen_for_keys()