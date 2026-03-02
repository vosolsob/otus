"""
Raspberry Camera Controller pro Raspberry Pi 4B, Camera V1.0 a A4988 ovladače.
Verze s podporou Picamera2, ovládáním motorů a monitorováním koncových spínačů.
"""

import tkinter as tk
from PIL import Image, ImageTk
import threading
import numpy as np
import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    # Fallback pro testování bez GPIO
    class GPIO:
        BCM = "BCM"
        IN = "IN"
        OUT = "OUT"
        LOW = 0
        HIGH = 1
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def input(pin): return 0
        @staticmethod
        def cleanup(): pass

from picamera2 import Picamera2

class CameraController:
    def __init__(self, preview_size=(320, 240)):
        self.picam2 = Picamera2()
        self.preview_size = preview_size
        self.picam2.configure(self.picam2.create_preview_configuration(main={"size": self.preview_size, "format": "RGB888"}))
        self.picam2.start()
        self.frame = None
        self.stream_running = False

    def start_preview(self):
        self.stream_running = True
        threading.Thread(target=self._update_stream, daemon=True).start()

    def stop_preview(self):
        self.stream_running = False

    def _update_stream(self):
        while self.stream_running:
            try:
                frame = self.picam2.capture_array()
                self.frame = frame.copy()
            except Exception:
                pass
            time.sleep(0.03)  # ~30 fps

    def get_frame(self):
        return self.frame

    def close(self):
        self.stop_preview()
        self.picam2.stop()

class StepperMotorController:
    """
    Řízení krokového motoru A4988.
    - DIR pin: řídí směr otáčení
    - STEP pin: generuje kroky
    - ENABLE pin: povolení/zakázání motoru
    - limit_switch_pin: pin pro detekci koncového spínače (paralelní zapojení)
    """
    def __init__(self, axis, dir_pin, step_pin, enable_pin, limit_switch_pin, steps_per_unit=100):
        self.axis = axis
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.enable_pin = enable_pin
        self.limit_switch_pin = limit_switch_pin
        self.steps_per_unit = steps_per_unit
        
        self.position = 0  # v jednotkách
        self.is_moving = False
        self.limit_triggered = False
        
        # Inicializace GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.enable_pin, GPIO.OUT)
        GPIO.setup(self.limit_switch_pin, GPIO.IN)
        
        self.motor_enabled = False
        self.disable()

    def enable(self):
        if not self.motor_enabled:
            GPIO.output(self.enable_pin, GPIO.LOW)  # A4988: LOW = povolení
            self.motor_enabled = True

    def disable(self):
        if self.motor_enabled:
            GPIO.output(self.enable_pin, GPIO.HIGH)  # A4988: HIGH = zakázání
            self.motor_enabled = False

    def check_limit_switch(self):
        """Ověří, zda je koncový spínač aktivován."""
        # Normálně otevřené (NO) - je logicky 0 (GND), když je aktivováno
        state = GPIO.input(self.limit_switch_pin)
        self.limit_triggered = (state == GPIO.LOW)
        return self.limit_triggered

    def move(self, units, direction=1):
        """
        Pohyb motoru o zadaný počet jednotek.
        direction: 1 = forward, -1 = backward
        Vrátí True, pokud byl pohyb proveden, False pokud byl zablokován limitem.
        """
        if self.check_limit_switch():
            print(f"[{self.axis}] Koncový spínač AKTIVOVÁN! Pohyb blokován.")
            self.limit_triggered = True
            return False
        
        self.enable()
        direction = 1 if direction > 0 else 0
        GPIO.output(self.dir_pin, direction)
        
        steps_to_move = abs(units) * self.steps_per_unit
        
        for _ in range(steps_to_move):
            # Opakované testování limitu během pohybu
            if self.check_limit_switch():
                print(f"[{self.axis}] Limit se aktivoval během pohybu! Zastavuji.")
                GPIO.output(self.step_pin, GPIO.LOW)
                self.disable()
                return False
            
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(0.001)  # Pulz s periodou ~2ms
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(0.001)
        
        self.position += units * direction
        self.disable()
        return True

    def home(self):
        """Vrátí motor do domácí pozice (limit switch)."""
        print(f"[{self.axis}] Hledám domácí pozici...")
        self.enable()
        GPIO.output(self.dir_pin, GPIO.LOW)  # Jedním směrem k limitu
        
        step_count = 0
        max_steps = 50000  # Ochrana před nekonečnou smyčkou
        
        while step_count < max_steps:
            if self.check_limit_switch():
                print(f"[{self.axis}] Domácí pozice dosažena!")
                self.position = 0
                self.disable()
                return True
            
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(0.001)
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(0.001)
            step_count += 1
        
        print(f"[{self.axis}] CHYBA: Domácí pozice nenalezena po {max_steps} krocích!")
        self.disable()
        return False

    def cleanup(self):
        """Vypnutí a vyčištění GPIO."""
        self.disable()
        GPIO.cleanup()

class ROIManager:
    def __init__(self):
        self.rois = []
        self.current_points = []

    def add_point(self, x, y, z):
        self.current_points.append((x, y, z))
        if len(self.current_points) == 2:
            self.rois.append(tuple(self.current_points))
            self.current_points = []

    def reset(self):
        self.rois = []
        self.current_points = []

    def get_rois(self):
        return self.rois

class CameraRigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raspberry Pi Camera Controller – ROI režim + Motor control")
        self.geometry("450x450")
        self.resizable(False, False)

        self.position = [0, 0, 0]  # x, y, z
        self.roi_manager = ROIManager()
        self.camera = CameraController()
        
        # Inicializace motorů
        # POZOR: Přizpůsit piny dle skutečného zapojení!
        try:
            self.x_motor = StepperMotorController("X", dir_pin=17, step_pin=27, enable_pin=22, limit_switch_pin=10)
            self.y_motor = StepperMotorController("Y", dir_pin=5, step_pin=6, enable_pin=22, limit_switch_pin=11)
            self.z_motor = StepperMotorController("Z", dir_pin=19, step_pin=26, enable_pin=22, limit_switch_pin=12)
            self.motors_initialized = True
        except Exception as e:
            print(f"Chyba při inicializaci motorů: {e}")
            self.motors_initialized = False

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_all("<Key>", self.on_key_press)
        self.camera.start_preview()
        self.update_preview()
        
        # Spustit monitorování limitů
        self.limit_check_running = True
        threading.Thread(target=self.monitor_limits, daemon=True).start()

    def create_widgets(self):
        self.preview_label = tk.Label(self, text="[Live kamera]", bg="gray", width=56, height=12)
        self.preview_label.pack(pady=5)
        
        self.position_label = tk.Label(self, text="Pozice: X=0, Y=0, Z=0", font=("Arial", 10))
        self.position_label.pack()
        
        self.status_label = tk.Label(self, text="Status: Ready", font=("Arial", 9), fg="green")
        self.status_label.pack()
        
        self.limit_status = tk.Label(self, text="Limity: OK", font=("Arial", 9), fg="green")
        self.limit_status.pack()
        
        self.roi_label = tk.Label(self, text="ROI: žádné")
        self.roi_label.pack(pady=2)
        
        tk.Label(self, text="Ovládání: ← → (X), ↑ ↓ (Y), A/Y (Z), B/N (bod), Space (ok), R (reset ROI)").pack(pady=3)
        
        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="Home All", command=self.home_all_axes, width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Reset ROI", command=self.reset_roi, width=12).pack(side=tk.LEFT, padx=2)

    def update_gui(self):
        self.position_label.config(text="Pozice: X={}, Y={}, Z={}".format(*self.position))
        rois = self.roi_manager.get_rois()
        self.roi_label.config(text="ROI: {}".format(rois if rois else "žádné"))

    def update_preview(self):
        frame = self.camera.get_frame()
        if frame is not None:
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.preview_label.imgtk = imgtk
            self.preview_label.config(image=imgtk)
        self.after(33, self.update_preview)

    def monitor_limits(self):
        """Neustálé monitorování stavu limitů."""
        while self.limit_check_running:
            if self.motors_initialized:
                x_limit = self.x_motor.check_limit_switch()
                y_limit = self.y_motor.check_limit_switch()
                z_limit = self.z_motor.check_limit_switch()
                
                status_text = "Limity: "
                color = "green"
                
                limit_states = []
                if x_limit:
                    limit_states.append("X")
                    color = "red"
                if y_limit:
                    limit_states.append("Y")
                    color = "red"
                if z_limit:
                    limit_states.append("Z")
                    color = "red"
                
                if limit_states:
                    status_text += ", ".join(limit_states) + " aktivován!"
                else:
                    status_text += "OK"
                
                self.limit_status.config(text=status_text, fg=color)
            
            time.sleep(0.1)

    def move_axis(self, axis, units):
        """Příkaz k pohybu osy."""
        if not self.motors_initialized:
            self.status_label.config(text="Status: Motory nejsou inicializovány!", fg="red")
            return
        
        if axis == "X":
            success = self.x_motor.move(units, direction=1 if units > 0 else -1)
            if success:
                self.position[0] += units
                self.status_label.config(text=f"Status: Pohyb X o {units}", fg="green")
            else:
                self.status_label.config(text="Status: Pohyb zablokován limitem!", fg="red")
        
        elif axis == "Y":
            success = self.y_motor.move(units, direction=1 if units > 0 else -1)
            if success:
                self.position[1] += units
                self.status_label.config(text=f"Status: Pohyb Y o {units}", fg="green")
            else:
                self.status_label.config(text="Status: Pohyb zablokován limitem!", fg="red")
        
        elif axis == "Z":
            success = self.z_motor.move(units, direction=1 if units > 0 else -1)
            if success:
                self.position[2] += units
                self.status_label.config(text=f"Status: Pohyb Z o {units}", fg="green")
            else:
                self.status_label.config(text="Status: Pohyb zablokován limitem!", fg="red")
        
        self.update_gui()

    def home_all_axes(self):
        """Vrátí všechny motory do domácí pozice."""
        if not self.motors_initialized:
            self.status_label.config(text="Status: Motory nejsou inicializovány!", fg="red")
            return
        
        self.status_label.config(text="Status: Hledám home pozice...", fg="blue")
        
        for motor in [self.x_motor, self.y_motor, self.z_motor]:
            motor.home()
        
        self.position = [0, 0, 0]
        self.status_label.config(text="Status: Home dosažena!", fg="green")
        self.update_gui()

    def on_key_press(self, event):
        if event.keysym == "Left":
            self.move_axis("X", -1)
        elif event.keysym == "Right":
            self.move_axis("X", 1)
        elif event.keysym == "Up":
            self.move_axis("Y", 1)
        elif event.keysym == "Down":
            self.move_axis("Y", -1)
        elif event.char == "q":
            self.move_axis("Z", 1)
        elif event.char == "a":
            self.move_axis("Z", -1)
        elif event.char == "b" or event.char == "n":
            self.set_roi_edge()
        elif event.keysym == "space":
            self.confirm_roi()
        elif event.char == "r":
            self.reset_roi()

    def set_roi_edge(self):
        x, y, z = self.position
        self.roi_manager.add_point(x, y, z)
        self.status_label.config(text="Status: Bod ROI zaznamenán", fg="blue")
        self.update_gui()

    def confirm_roi(self):
        self.status_label.config(text="Status: ROI potvrzeno", fg="blue")

    def reset_roi(self):
        self.roi_manager.reset()
        self.status_label.config(text="Status: ROI resetováno", fg="blue")
        self.update_gui()

    def on_close(self):
        self.limit_check_running = False
        self.camera.close()
        if self.motors_initialized:
            self.x_motor.cleanup()
            self.y_motor.cleanup()
            self.z_motor.cleanup()
        self.destroy()

if __name__ == "__main__":
    app = CameraRigApp()
    app.mainloop()
