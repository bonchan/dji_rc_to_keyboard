import time
import serial.tools.list_ports
from src.remote_controller.dji_rc3 import DJIRC3
from src.remote_controller.dji_rcN1 import DJIRCN1
from src.remote_controller.dji_m300 import DJIM300

from src.keyboard.keyboard import KeyboardEmulator, Key

def find_n1_port():
    """Scans for the DJI 'For Protocol' COM port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "For Protocol" in port.description or "DJI" in port.description:
            return port.device
    return None

def main():
    print("--- DJI Remote Controller Universal Interface ---")
    
    # 1. Try to detect N1 first via Serial
    n1_port = find_n1_port()
    
    if n1_port:
        print(f"Detected N1 hardware on {n1_port}. Initializing N1 Mode...")
        rc = DJIRCN1(port=n1_port)
    else:
        print("N1 Hardware not detected. Attempting to initialize RC3 via HID...")
        # 2. Fallback to RC3 (Assumes index 0)
        rc = DJIRC3(joystick_index=0, deadzone_threshold_movement=0.3, deadzone_threshold_elevation=0.6)

    # rc = DJIM300(port="COM5")

    k_emu = KeyboardEmulator(emulate_hardware=True, print_events=True)
    last_mode = None
    last_b1 = False # action
    last_b2 = False # pause
    last_b3 = False # trigger
    last_b4 = False # start/stop

    # Logic for the n-second hold
    hold_active = False
    hold_start_time = 0
    frozen_axes = {"pitch": 0, "roll": 0, "yaw": 0}

    # 3. Universal loop
    try:
        print("\nStreaming data. Press Ctrl+C to stop.\n")
        while True:
            if not rc.update(): continue
            current_time = time.time()

            # security stop, held down
            if rc.button1 != last_b1:
                k_emu.cleanup()
                # last_b2 = rc.button2
                continue

            if rc.button4 and not last_b4:
                if hold_active:
                    print(">>> REMOVE HOLD ACTIVE<<<")
                    hold_active = False
                else:
                    print(">>> HOLD ACTIVE (N Seconds) <<<")
                    hold_active = True
                    hold_start_time = current_time
                    # Capture current snapshots
                    frozen_axes["pitch"] = rc.pitch
                    frozen_axes["roll"] = rc.roll
                    frozen_axes["yaw"] = rc.yaw
            last_b4 = rc.button4

            # Check if hold should expire
            if hold_active and (current_time - hold_start_time > 7.5):
                print(">>> HOLD EXPIRED - Returning to Manual Control <<<")
                hold_active = False

            # --- 2. Determine Axis Values ---
            if hold_active:
                pitch_val = frozen_axes["pitch"]
                roll_val = frozen_axes["roll"]
                yaw_val = frozen_axes["yaw"]
            else:
                pitch_val = rc.pitch
                roll_val = rc.roll
                yaw_val = rc.yaw
            
            # 1. Handle Axes (Continuous state)
            k_emu.handle_axis(pitch_val, 'w', 's')
            k_emu.handle_axis(roll_val, 'd', 'a')
            k_emu.handle_axis(yaw_val, 'e', 'q')
            if last_mode == 1:
                k_emu.handle_axis(yaw_val, Key.right, Key.left) # Fast phase

            # Elevation
            k_emu.handle_axis(rc.throttle, 'c', 'z')
            k_emu.handle_axis(rc.tilt, Key.down, Key.up) # Using Sw2 as Aux

            # 2. Handle Mode Switch (One-shot Tap)
            if rc.sw1 != last_mode:
                target = {1: '1', 0: '2', -1: '3'}.get(rc.sw1)
                if target: k_emu.tap(target)
                last_mode = rc.sw1

            # 3. Handle Buttons (One-shot Tap)
            if rc.button2 and not last_b2:
                k_emu.tap('t')
            last_b2 = rc.button2

            if rc.button3 and not last_b3:
                k_emu.tap('f')
            last_b3 = rc.button3
            
            time.sleep(0.01) # ~100Hz update rate

    except KeyboardInterrupt:
        print("\n\nUser interrupted. Closing connection...")
    finally:
        rc.close()
        k_emu.force_cleanup()
        print("Done.")

if __name__ == "__main__":
    main()