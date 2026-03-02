import curses
import time
from threading import Thread, Event
from gpiozero import OutputDevice, DigitalInputDevice

# ==== PIN DEFINICE ====
STEP_PIN = 26
DIR_PIN = 19
ENABLE_PIN = 22
LIMIT_PIN = 12  # paralelní koncové spínače

# ==== INICIALIZACE ====
step = OutputDevice(STEP_PIN)
direction = OutputDevice(DIR_PIN)
enable = OutputDevice(ENABLE_PIN, active_high=False)  # LOW = enable
# aktivní LOW → pull_up=True
limit_switch = DigitalInputDevice(LIMIT_PIN, pull_up=True)

enable.on()  # aktivace driveru

STEP_DELAY = 0.002  # pevná rychlost

# ==== FLAGY ====
move_up = Event()
move_down = Event()
stop_motor = Event()  # bude nastaven, pokud limit

# ==== FUNKCE PRO KROK ====
def make_step():
    step.on()
    time.sleep(STEP_DELAY)
    step.off()
    time.sleep(STEP_DELAY)

# ==== VLÁKNO PRO MOTOR ====
def motor_thread():
    while True:
        if stop_motor.is_set():
            time.sleep(0.001)
            continue

        if move_up.is_set():
            direction.on()
            if not limit_switch.value:  # sepnutý = LOW
                stop_motor.set()
                move_up.clear()
            else:
                make_step()

        elif move_down.is_set():
            direction.off()
            if not limit_switch.value:
                stop_motor.set()
                move_down.clear()
            else:
                make_step()
        else:
            time.sleep(0.001)  # nic se neděje

# ==== HLAVNÍ PROGRAM (curses) ====
def main(stdscr):
    t = Thread(target=motor_thread, daemon=True)
    t.start()

    curses.cbreak()
    stdscr.nodelay(True)
    stdscr.clear()
    stdscr.addstr("Ovládání osy Z\n")
    stdscr.addstr("↑ = nahoru, ↓ = dolů, q = konec\n")

    try:
        while True:
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                move_up.set()
                move_down.clear()
                stop_motor.clear()
                stdscr.addstr(5, 0, "Jede nahoru       ")
                stdscr.refresh()
            elif key == curses.KEY_DOWN:
                move_down.set()
                move_up.clear()
                stop_motor.clear()
                stdscr.addstr(5, 0, "Jede dolů        ")
                stdscr.refresh()
            else:
                # pokud klávesa není držena → zastavení
                move_up.clear()
                move_down.clear()

            # detekce limitu
            if not limit_switch.value:  # LOW = sepnutý
                stop_motor.set()
                stdscr.addstr(6, 0, "Koncový spínač aktivní! STOP  ")
                stdscr.refresh()

            time.sleep(0.01)

    finally:
        enable.off()
        stdscr.addstr(7, 0, "Program ukončen")
        stdscr.refresh()
        time.sleep(1)

curses.wrapper(main)
