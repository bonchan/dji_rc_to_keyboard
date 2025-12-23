import pygame


def dead_zone(value, threshold=0.2):
    return 0.0 if abs(value) < threshold else value


class DJIFPVRemoteController3:
    def __init__(self):
        # Analog joystick values (float: range -1.0 to 1.0)
        self.throttle = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.tilt = 0.0

        # Digital buttons (bool)
        self.c1 = False
        self.pause = False
        self.trigger = False
        self.start_stop = False

        # Mode switches (int)
        self.mode = 0
        self.aux = 0

    def update_from_joystick(self, js):
        pygame.event.pump()

        self.throttle = dead_zone(js.get_axis(2))
        self.yaw = dead_zone(js.get_axis(3))
        self.pitch = dead_zone(js.get_axis(1))
        self.roll = dead_zone(js.get_axis(0))
        self.tilt = dead_zone(js.get_axis(4))

        self.c1 = bool(js.get_button(0))
        self.pause = bool(js.get_button(2))
        self.trigger = bool(js.get_button(3))
        self.start_stop = bool(js.get_button(1))
        self.mode = -1 if bool(js.get_button(7)) else 1 if bool(js.get_button(6)) else 0
        self.aux = 1 if bool(js.get_button(5)) else 0 if bool(js.get_button(4)) else -1

    def __str__(self):
        return (
            f"Throttle: {self.throttle:.2f}, Yaw: {self.yaw:.2f}, "
            f"Pitch: {self.pitch:.2f}, Roll: {self.roll:.2f}, Tilt: {self.tilt:.2f},\n"
            f"C1: {self.c1}, Pause: {self.pause}, Trigger: {self.trigger}, Start/Stop: {self.start_stop},\n"
            f"Mode: {self.mode}, Aux: {self.aux}"
        )