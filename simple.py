import curses
import time
from gpiozero import OutputDevice, DigitalInputDevice

# ==== PIN DEFINICE ====
STEP_PIN = 20
DIR_PIN = 21
ENABLE_PIN = 16
LIMIT_PIN = 12   # oba koncové spínače paralelně

# ==== INICIALIZACE ====
step = OutputDevice(STEP_PIN)
direction = OutputDevice(DIR_PIN)
enable = OutputDevice(ENABLE_PIN, active_high=False)  # LOW = enable
limit_switch = DigitalInputDevice(LIMIT_PIN, pull_up=False)

enable.on()  # aktivace driveru

STEP_DELAY = 0.001  # rychlost motoru (menší = rychlejší)

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
    stdscr.addstr("↑ = nahoru\n")
    stdscr.addstr("↓ = dolů\n")
    stdscr.addstr("q = konec\n")

    try:
        while True:
            key = stdscr.getch()

            if key == curses.KEY_UP:
                direction.on()   # směr nahoru

                while True:
                    if limit_switch.value:   # pokud je HIGH
                        stdscr.addstr(5, 0, "Koncový spínač aktivní! STOP ")
                        stdscr.refresh()
                        break

                    make_step()

                    if stdscr.getch() != curses.KEY_UP:
                        break

            elif key == curses.KEY_DOWN:
                direction.off()  # směr dolů

                while True:
                    if limit_switch.value:
                        stdscr.addstr(5, 0, "Koncový spínač aktivní! STOP ")
                        stdscr.refresh()
                        break

                    make_step()

                    if stdscr.getch() != curses.KEY_DOWN:
                        break

            elif key == ord('q'):
                break

            time.sleep(0.01)

    finally:
        enable.off()  # vypnutí driveru


curses.wrapper(main)
