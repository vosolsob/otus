import curses
import time
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
limit_switch = DigitalInputDevice(LIMIT_PIN, pull_up=True)  # sepnutý = LOW

enable.on()  # aktivace driveru

STEP_DELAY = 0.002  # pevná rychlost

# ==== FUNKCE PRO KROK ====
def make_step():
    step.on()
    time.sleep(STEP_DELAY)
    step.off()
    time.sleep(STEP_DELAY)

# ==== HLAVNÍ PROGRAM ====
def main(stdscr):
    curses.cbreak()
    stdscr.nodelay(True)
    stdscr.clear()
    stdscr.addstr("Ovládání osy Z\n")
    stdscr.addstr("↑ = nahoru, ↓ = dolů, q = konec\n")

    try:
        while True:
            key = stdscr.getch()
            # kontrola ukončení
            if key == ord('q'):
                break

            # rozhodnutí o směru
            if key == curses.KEY_UP:
                direction.on()
                stdscr.addstr(5, 0, "Jede nahoru   ")
                stdscr.refresh()
                while True:
                    # pokud je koncový spínač sepnutý, okamžitě stop
                    if not limit_switch.value:  # LOW = aktivní
                        stdscr.addstr(6, 0, "Koncový spínač aktivní! STOP  ")
                        stdscr.refresh()
                        break
                    make_step()
                    # pokud už není stisknutá šipka, break
                    if stdscr.getch() != curses.KEY_UP:
                        break

            elif key == curses.KEY_DOWN:
                direction.off()
                stdscr.addstr(5, 0, "Jede dolů   ")
                stdscr.refresh()
                while True:
                    if not limit_switch.value:  # LOW = aktivní
                        stdscr.addstr(6, 0, "Koncový spínač aktivní! STOP  ")
                        stdscr.refresh()
                        break
                    make_step()
                    if stdscr.getch() != curses.KEY_DOWN:
                        break

            time.sleep(0.001)  # minimalní pauza pro stabilitu

    finally:
        enable.off()
        stdscr.addstr(7, 0, "Program ukončen")
        stdscr.refresh()
        time.sleep(1)

curses.wrapper(main)
