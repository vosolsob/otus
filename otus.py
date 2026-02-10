"""
Raspberry Camera Controller pro Raspberry Pi 4B, Camera V1.0 a A4988 ovladače.
Verze s podporou Picamera2 pro live preview v režimu výběru ROI.
"""

import tkinter as tk
from PIL import Image, ImageTk
import threading
import numpy as np
import time

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

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

class StepperMotor:
    def __init__(self, axis, pins, limit_min, limit_max):
        self.axis = axis

    def move(self, steps):
        pass

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
        self.title("Raspberry Pi Camera Controller – ROI režim (preview, Picamera2)")
        self.geometry("400x320")
        self.resizable(False, False)

        self.position = [0, 0, 0]  # x, y, z
        self.roi_manager = ROIManager()
        self.camera = CameraController()

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_all("<Key>", self.on_key_press)
        self.camera.start_preview()
        self.update_preview()

    def create_widgets(self):
        self.preview_label = tk.Label(self, text="[Zde bude live kamera]", bg="gray", width=48, height=14)
        self.preview_label.pack(pady=6)
        self.position_label = tk.Label(self, text="Pozice: X=0, Y=0, Z=0")
        self.position_label.pack()
        self.roi_label = tk.Label(self, text="ROI: žádné")
        self.roi_label.pack(pady=2)
        tk.Button(self, text="Reset ROI", command=self.reset_roi).pack(pady=3)

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

    def on_key_press(self, event):
        if event.keysym == "Left":
            self.position[0] -= 1
        elif event.keysym == "Right":
            self.position[0] += 1
        elif event.keysym == "Up":
            self.position[1] += 1
        elif event.keysym == "Down":
            self.position[1] -= 1
        elif event.char == "b" or event.char == "n":
            self.set_roi_edge()
        elif event.keysym == "space":
            self.confirm_roi()
        self.update_gui()

    def set_roi_edge(self):
        x, y, z = self.position
        self.roi_manager.add_point(x, y, z)
        self.update_gui()

    def confirm_roi(self):
        pass  # do budoucna

    def reset_roi(self):
        self.roi_manager.reset()
        self.update_gui()

    def on_close(self):
        self.camera.close()
        self.destroy()

if __name__ == "__main__":
    app = CameraRigApp()
    app.mainloop()