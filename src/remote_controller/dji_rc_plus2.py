import subprocess
import os
import threading
import re
from .base_rc import BaseRemoteController, RCConnectionError

# Standard DJI buttons for your handler
buttons_config = [
    ['button1', False],
    ['button2', False],
    ['button3', False],
    ['button4', False],
    ['button5', False],
]

class DJIRCPlus2(BaseRemoteController):
    def __init__(self, deadzone_threshold_movement=0.1, deadzone_threshold_elevation=0.1, deadzone_threshold_tilt=0.1, connect_mode="USB", ip=''):
        super().__init__(buttons_config, deadzone_threshold_movement, deadzone_threshold_elevation, deadzone_threshold_tilt)
        
        # ADB is in the platform-tools folder relative to the root
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.adb_path = os.path.join(self.root_dir, "platform-tools", "adb.exe")
        self.connect_mode = connect_mode
        self.ip = ip
        
        if not os.path.exists(self.adb_path):
            raise RCConnectionError(f"ADB binary not found at {self.adb_path}")

        self.process = None
        self._connected = False
        self._stop_thread = False
        
        # Internal state for ButtonHandler syncing
        self._raw_button_states = {1: False, 2: False, 3: False, 4: False, 5: False}
        self.is_touching = False
        self.current_touch_x = -1
        self.current_touch_y = -1
        self.raw_touch_x = -1
        self.raw_touch_y = -1

        if self.connect_mode == "WIFI":
            # Force an ADB connection attempt before starting the thread
            subprocess.run([self.adb_path, "connect", self.ip], capture_output=True)

        # Start background sniffer
        self.thread = threading.Thread(target=self._sniffer_loop, daemon=True)
        self.thread.start()
        
        # Wait a moment for ADB to initialize so main.py doesn't exit immediately
        time_out = 0
        while not self._connected and time_out < 5:
            import time
            time.sleep(0.5)
            time_out += 0.5

    def _sniffer_loop(self):
        try:
            if self.connect_mode == "WIFI":
                # Target the specific IP
                cmd = [self.adb_path, "-s", self.ip, "shell", "getevent", "-lt"]
            else:
                # Target the physical USB device specifically (-d)
                cmd = [self.adb_path, "-d", "shell", "getevent", "-lt"]
                
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self._connected = True

            for line in self.process.stdout:
                if self._stop_thread: break
                self._parse_line(line)

        except Exception as e:
            self._connected = False
            if self.logger: self.logger.error(f"ADB Thread Error: {e}")

    def _parse_line(self, line):

        abs_match = re.search(r"EV_ABS\s+(ABS_\w+)\s+([0-9a-fA-F]+)", line)
        if abs_match:
            code = abs_match.group(1)
            # Clean the string and convert to int
            raw_str = abs_match.group(2).strip()
            value = int(raw_str, 16)

            # print(code, value)

            if   code == "ABS_RX":    self.roll = self.dead_zone_movement(self._normalize_stick(value))
            elif code == "ABS_RY":    self.pitch = -self.dead_zone_movement(self._normalize_stick(value))
            elif code == "ABS_Y":    self.throttle = -self.dead_zone_elevation(self._normalize_stick(value))
            elif code == "ABS_X":   self.yaw = self.dead_zone_movement(self._normalize_stick(value))
            elif code == "ABS_Z": self.tilt = self.dead_zone_tilt(self._normalize_wheel(value))

        # # 2. Handle Digital Buttons (EV_KEY)
        # # Matches e.g.: EV_KEY BTN_SOUTH DOWN  /  EV_KEY BTN_SOUTH UP
        key_match = re.search(r"EV_KEY\s+(\w+)\s+(DOWN|UP|00000001|00000000)", line)
        if key_match:
            btn_code = key_match.group(1)
            is_down = "DOWN" in key_match.group(2) or "1" in key_match.group(2)
            # print(btn_code, is_down)
            
            if btn_code == "KEY_BACK": self._raw_button_states[1] = is_down
            if btn_code == "BTN_TR": self._raw_button_states[3] = is_down
            if btn_code == "BTN_TL": self._raw_button_states[5] = is_down
            if btn_code == "KEY_F1": self.sw1 = 1
            if btn_code == "KEY_F2": self.sw1 = 0
            if btn_code == "KEY_F3": self.sw1 = -1

        # Touch Logic
        touch_match = re.search(r"ABS_MT_POSITION_(X|Y)\s+([0-9a-fA-F]+)", line)
        if touch_match:
            axis = touch_match.group(1)
            val = int(touch_match.group(2), 16)
            
            if axis == "X":
                self.raw_touch_x = val
            elif axis == "Y":
                self.raw_touch_y = val
            
            self.current_touch_x, self.current_touch_y = self.normalize_touch_signed(self.raw_touch_x, self.raw_touch_y)

        # Detect the 'Finger Lifted' event
        match = re.search(r"ABS_MT_TRACKING_ID\s+([0-9a-fA-F]+)", line)

        if match:
            raw_hex = match.group(1).strip().lower()
            
            if raw_hex == "ffffffff":
                self.is_touching = False
            else:
                self.is_touching = True

        # if self.is_touching:
        #     print(self.current_touch_x, self.current_touch_y)


        #     # Map physical labels to your button numbers123
        #     # Note: You may need to press them and see the labels in your console to confirm
        #     if btn_code == "BTN_SOUTH": self._raw_button_states[1] = is_down # C1
        #     if btn_code == "BTN_EAST":  self._raw_button_states[2] = is_down # C2
        #     if btn_code == "BTN_NORTH": self._raw_button_states[3] = is_down # Rec
        #     if btn_code == "BTN_WEST":  self._raw_button_states[4] = is_down # Shutter

    def _normalize_stick(self, val):
        # center = -1
        # max = 32767
        # min = -32768

        if val > 0x7FFFFFFF:
            val -= 0x100000000
        
        center = -1
        # We use 32767.0 as the divisor for a 1.0 to -1.0 spread
        normalized = (val - center) / 32767.0
        
        # Clamp to ensure no float overflow
        return max(min(normalized, 1.0), -1.0)
    
    def _normalize_wheel(self, val):
        # center = 127
        # max = 254
        # min = 0
        
        center = 127
        # We use 32767.0 as the divisor for a 1.0 to -1.0 spread
        normalized = (val - center) / 254.0
        
        # Clamp to ensure no float overflow
        return max(min(normalized, 1.0), -1.0)
    
    def normalize_touch_signed(self, x_raw, y_raw):
        W_MAX = 1100.0
        H_MAX = 1900.0
        x_signed = (x_raw / W_MAX * 2.0) - 1.0
        y_signed = (y_raw / H_MAX * 2.0) - 1.0
        return max(min(x_signed, 1.0), -1.0), max(min(y_signed, 1.0), -1.0)

    def update(self) -> bool:
        """
        Updates the ButtonHandler objects with the raw states 
        collected by the background thread.
        """
        if not self.is_connected:
            return False
            
        self.button1.update(self._raw_button_states[1])
        self.button2.update(self._raw_button_states[2])
        self.button3.update(self._raw_button_states[3])
        self.button4.update(self._raw_button_states[4])
        self.button5.update(self._raw_button_states[5])
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected and self.process.poll() is None

    def close(self):
        self._stop_thread = True
        if self.process:
            self.process.terminate()