class BaseRemoteController:
    """
    Standard interface for DJI Remote Controllers.
    All values are normalized to a float range of -1.0 to 1.0.
    """
    def __init__(self, deadzone_threshold_movement, deadzone_threshold_elevation):

        self.deadzone_threshold_movement = deadzone_threshold_movement
        self.deadzone_threshold_elevation = deadzone_threshold_elevation

        # --- Analog Axes ---
        self.throttle = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.tilt = 0.0

        # --- Digital Buttons ---
        self.button1 = False
        self.button2 = False
        self.button3 = False
        self.button4 = False

        # --- Mode Switches ---
        # Represented as integers: -1 (Left/Up), 0 (Center), 1 (Right/Down)
        self.sw1 = 0
        self.sw2 = 0

    def update(self):
        """
        To be overridden by DJIRCN1 and DJIRC3.
        Should update the attributes above and return True if successful.
        """
        raise NotImplementedError("Child classes must implement the update method.")
    
    def dead_zone_movement(self, value):
        return self._dead_zone(value, self.deadzone_threshold_movement)
    
    def dead_zone_elevation(self, value):
        return self._dead_zone(value, self.deadzone_threshold_elevation)
    
    def _dead_zone(self, value, threshold):
        return 0.0 if abs(value) < threshold else value

    def __str__(self):
        """Standardized string output for debugging across all models."""
        axes = f"T: {self.throttle: .2f} | Y: {self.yaw: .2f} | P: {self.pitch: .2f} | R: {self.roll: .2f} | Tilt: {self.tilt: .2f}"
        btns = f"B1: {int(self.button1)} B2: {int(self.button2)} B3: {int(self.button3)} B4: {int(self.button4)}"
        swts = f"SW1: {self.sw1} SW2: {self.sw2}"
        return f"{axes} | {btns} | {swts} | {self.deadzone_threshold_movement} | {self.deadzone_threshold_elevation}"
    
