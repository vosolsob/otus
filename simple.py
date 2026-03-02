import curses
import pigpio
import time
from threading import Thread, Event

# ==== PIN DEFINICE ====
STEP_PIN = 26
DIR_PIN = 19
ENABLE_PIN = 22
LIMIT_PIN = 12  # paralelní koncové spínače

# ==== PARAMETRY MOTORU ====
STEP_DELAY = 0.002  # pevná rychlost (s)

# ==== FLAGY ====
move_up = Event()
move_down = Event()
stop_motor = Event()

# ==== INICIALIZACE pigpio ====
pi = pigpio.pi()
pi.set_mode(STEP_PIN, pigpio.OUTPUT)
pi.set_mode(DIR_PIN, pigpio.OUTPUT)
pi.set_mode(ENABLE_PIN, pigpio.OUTPUT)
pi.set_mode(LIMIT_PIN, pigpio.INPUT)
pi.write(ENABLE_PIN, 0)  # LOW = enable driver

# externí pull-up → LOW = sepnutý
def is_limit_triggered():
    # software debounce 5 ms
    if pi.read(LIMIT_PIN) == 0:  # LOW = sepnutý
        time.sleep(0.005)
        if pi.read(LIMIT_PIN) == 0:
            return True
    return False

# ==== VLÁKNO MOTORU ====
def motor_loop():
    while True:
        if stop_motor.is_set():
            time.sleep(0.001)
            continue

        if move_up.is_set():
            pi.write(DIR_PIN, 1)
            if is_limit_triggered():
                stop_motor.set()
                move_up.clear()
                continue
            # STEP pulse
            pi.write(STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            pi.write(STEP_PIN, 0)
            time.sleep(STEP_DELAY)

        elif move_down.is_set():
            pi.write(DIR_PIN, 0)
            if is_limit_triggered():
                stop_motor.set()
                move_down.clear()
                continue
            # STEP pulse
            pi.write(STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            pi.write(STEP_PIN, 0)
            time.sleep(STEP_DELAY)

        else:
            time.sleep(0.001)

# ==== HLAVNÍ PROGRAM (curses) ====
def main(stdscr):
    t = Thread(target=motor_loop, daemon=True)
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
                # žádná klávesa → zastavení
                move_up.clear()
                move_down.clear()

            # detekce limitu v hlavním vlákně
            if is_limit_triggered():
                stop_motor.set()
                stdscr.addstr(6, 0, "Koncový spínač aktivní! STOP  ")
                stdscr.refresh()

            time.sleep(0.001)

    finally:
        pi.write(ENABLE_PIN, 1)  # vypnutí driveru
        pi.stop()
        stdscr.addstr(7, 0, "Program ukončen")
        stdscr.refresh()
        time.sleep(1)

curses.wrapper(main)
