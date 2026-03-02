import curses
import time
import pigpio
from threading import Thread, Event

# ==== PIN DEFINICE ====
STEP_PIN = 26
DIR_PIN = 19
ENABLE_PIN = 22
LIMIT_PIN = 12  # paralelní spínače

# ==== PARAMETRY ====
STEP_FREQ = 500  # Hz, frekvence kroků
STEP_WIDTH = 1   # ms pulsu (délka HIGH)

# ==== FLAGY ====
move_up = Event()
move_down = Event()
stop_motor = Event()

# ==== INIT pigpio ====
pi = pigpio.pi()
pi.set_mode(STEP_PIN, pigpio.OUTPUT)
pi.set_mode(DIR_PIN, pigpio.OUTPUT)
pi.set_mode(ENABLE_PIN, pigpio.OUTPUT)
pi.set_mode(LIMIT_PIN, pigpio.INPUT)
pi.write(ENABLE_PIN, 0)  # LOW = enable driver

# ==== FUNKCE PRO LIMIT SWITCH ====
def is_limit_triggered():
    # software debounce 5 ms
    if pi.read(LIMIT_PIN) == 0:  # LOW = sepnutý
        time.sleep(0.005)
        if pi.read(LIMIT_PIN) == 0:
            return True
    return False

# ==== GENERACE WAVY STEP ====
def create_step_wave(freq_hz):
    micros = int(500000 / freq_hz)  # polovina periody v µs
    pulses = []
    pulses.append(pigpio.pulse(1 << STEP_PIN, 0, micros))
    pulses.append(pigpio.pulse(0, 1 << STEP_PIN, micros))
    pi.wave_add_generic(pulses)
    return pi.wave_create()

# ==== MOTOR THREAD ====
def motor_loop():
    wave_id = create_step_wave(STEP_FREQ)
    while True:
        if stop_motor.is_set():
            pi.wave_tx_stop()
            time.sleep(0.001)
            continue

        if move_up.is_set():
            pi.write(DIR_PIN, 1)
            if is_limit_triggered():
                stop_motor.set()
                move_up.clear()
                pi.wave_tx_stop()
                continue
            if not pi.wave_tx_busy():
                pi.wave_send_repeat(wave_id)

        elif move_down.is_set():
            pi.write(DIR_PIN, 0)
            if is_limit_triggered():
                stop_motor.set()
                move_down.clear()
                pi.wave_tx_stop()
                continue
            if not pi.wave_tx_busy():
                pi.wave_send_repeat(wave_id)

        else:
            pi.wave_tx_stop()
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
                move_up.clear()
                move_down.clear()

            # detekce limitu
            if is_limit_triggered():
                stop_motor.set()
                stdscr.addstr(6, 0, "Koncový spínač aktivní! STOP  ")
                stdscr.refresh()

            time.sleep(0.001)

    finally:
        pi.wave_tx_stop()
        pi.write(ENABLE_PIN, 1)
        pi.stop()
        stdscr.addstr(7, 0, "Program ukončen")
        stdscr.refresh()
        time.sleep(1)

curses.wrapper(main)
