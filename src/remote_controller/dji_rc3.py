import pygame
from .base_rc import BaseRemoteController


class DJIRC3(BaseRemoteController):
    def __init__(self, joystick_index=0, deadzone_threshold_movement=0.1, deadzone_threshold_elevation=0.1):
        super().__init__(deadzone_threshold_movement=deadzone_threshold_movement, deadzone_threshold_elevation=deadzone_threshold_elevation)
        
        if not pygame.get_init():
            pygame.init()
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        try:
            self.js = pygame.joystick.Joystick(joystick_index)
            self.js.init()
            print(f"Connected to: {self.js.get_name()}")
        except pygame.error:
            print("DJI RC3 not found at specified index.")
            self.js = None

    def update(self):
        if not self.js:
            return False

        pygame.event.pump()
        
        try:
            # --- Analog Axis Mapping ---
            # Standard DJI RC3 HID Layout
            self.roll     = self.dead_zone_movement(self.js.get_axis(0))
            self.pitch    = self.dead_zone_movement(self.js.get_axis(1))
            self.throttle = self.dead_zone_elevation(self.js.get_axis(2))
            self.yaw      = self.dead_zone_movement(self.js.get_axis(3))
            # self.tilt     = self.dead_zone(self.js.get_axis(4)) # Gimbal Wheel

            # --- Digital Button Mapping ---
            self.button1 = bool(self.js.get_button(0)) # c1
            self.button2 = bool(self.js.get_button(2)) # pause
            self.button3 = bool(self.js.get_button(3)) # trigger
            self.button4 = bool(self.js.get_button(1)) # start_stop

            # --- Switch Mapping ---
            self.sw1 = -1 if bool(self.js.get_button(7)) else 1 if bool(self.js.get_button(6)) else 0 # mode
            self.tilt = 1 if bool(self.js.get_button(5)) else 0 if bool(self.js.get_button(4)) else -1 # aux
            return True

        except pygame.error:
            return False

    def close(self):
        if self.js:
            self.js.quit()