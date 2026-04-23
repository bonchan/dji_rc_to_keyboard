import math
import time
import json
import asyncio
import websockets
from datetime import datetime

from src.keyboard.keyboard import KbButton


class DroneSimulator:
    def __init__(self, lat=0.0, lng=0.0, alt=0.0,
                 drone_sn="SIM-DRONE-001", dock_sn="SIM-DOCK-001"):

        self.drone_sn = drone_sn
        self.dock_sn = dock_sn
        self.home_distance = 0.0

        # --- Current State ---
        self.lat = lat
        self.lng = lng
        self.alt = alt

        self.attitude_head = 0
        self.attitude_pitch = 0
        self.attitude_roll = 0

        self.gimbal_pitch = 0
        self.gimbal_roll = 0
        self.gimbal_yaw = 0

        self.trigger = False

        # --- Velocity State (NEW: inertia) ---
        self.vx = 0.0  # east (m/s)
        self.vy = 0.0  # north (m/s)
        self.vz = 0.0  # vertical (m/s)

        # --- Camera ---
        self.camera_mode = 999
        self.last_zoom = 0
        self.last_zoom_list = [1, 3, 7, 14, 28, 56]
        self.last_zoom_index = 0

        # --- Measurement ---
        self.measure_target_altitude = None
        self.measure_target_distance = None
        self.measure_target_error_state = None
        self.measure_target_latitude = None
        self.measure_target_longitude = None

        self.payload_index = '99-0-0'

        # --- Physical Limits (tuned DOWN for sanity) ---
        self.MAX_ASCENT_SPEED = 10.0
        self.MAX_DESCENT_SPEED = 8.0
        self.MAX_HORIZONTAL_SPEED = 15.0

        # --- Dynamics (NEW) ---
        self.ACCEL_HORIZONTAL = 4.0   # m/s²
        self.ACCEL_VERTICAL = 3.0     # m/s²
        self.DRAG = 1.2              # higher = more braking

        # --- Controls ---
        self.turn_speed = 45.0
        self.tilt_speed = 10.0

        # --- Geo ---
        self.METERS_TO_DEG = 1.0 / 111111.0

        self.last_update = time.time()

    def update(self, rc):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Prevent physics explosion on lag spikes
        dt = min(dt, 0.05)

        # --- 1. Heading (Yaw) ---
        self.attitude_head += rc.yaw * self.turn_speed * dt
        self.attitude_head %= 360

        # --- 2. Vertical (Throttle with inertia) ---
        if rc.throttle > 0:
            target_vz = rc.throttle * self.MAX_ASCENT_SPEED
        else:
            target_vz = rc.throttle * self.MAX_DESCENT_SPEED

        # Smooth acceleration toward target
        self.vz += (target_vz - self.vz) * min(1.0, self.ACCEL_VERTICAL * dt)

        # Drag
        self.vz *= (1.0 - self.DRAG * dt)

        # Apply movement
        self.alt += self.vz * dt
        self.alt = max(0.0, self.alt)

        # --- 3. Horizontal (Pitch/Roll with inertia) ---
        target_pitch = rc.pitch * self.MAX_HORIZONTAL_SPEED
        target_roll = -rc.roll * self.MAX_HORIZONTAL_SPEED

        rad = math.radians(self.attitude_head)

        target_vy = (target_pitch * math.cos(rad)) + (target_roll * math.sin(rad))  # north
        target_vx = (target_pitch * math.sin(rad)) - (target_roll * math.cos(rad))  # east

        # Smooth acceleration
        self.vx += (target_vx - self.vx) * min(1.0, self.ACCEL_HORIZONTAL * dt)
        self.vy += (target_vy - self.vy) * min(1.0, self.ACCEL_HORIZONTAL * dt)

        # Drag
        drag_factor = (1.0 - self.DRAG * dt)
        self.vx *= drag_factor
        self.vy *= drag_factor

        # Clamp total horizontal speed
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > self.MAX_HORIZONTAL_SPEED:
            scale = self.MAX_HORIZONTAL_SPEED / speed
            self.vx *= scale
            self.vy *= scale

        # Update GPS
        lat_rad = math.radians(self.lat)
        self.lat += (self.vy * self.METERS_TO_DEG) * dt
        self.lng += (self.vx * self.METERS_TO_DEG / max(0.0001, math.cos(lat_rad))) * dt

        # --- 4. Gimbal ---
        self.gimbal_pitch += rc.tilt * self.tilt_speed * dt
        self.gimbal_pitch = max(-90.0, min(35.0, self.gimbal_pitch))

        # --- 5. Camera Mode ---
        if rc.sw1 != self.camera_mode:
            target = {
                1: KbButton.CAMERA_WIDE,
                0: KbButton.CAMERA_ZOOM,
                -1: KbButton.CAMERA_IR
            }.get(rc.sw1)

            if target:
                self.camera_mode = target.value

        # --- 6. Zoom (clamped index like you wanted) ---
        if rc.sw2 != self.last_zoom:
            self.last_zoom_index -= rc.sw2
            self.last_zoom_index = max(0, min(self.last_zoom_index, len(self.last_zoom_list) - 1))
            self.last_zoom = rc.sw2

        # if rc.button3 != self.button3:
        self.trigger = rc.button3.is_short_tap

    def __str__(self):
        return (
            f"GPS: {self.lat:.7f}, {self.lng:.7f} | "
            f"ALT: {self.alt:5.2f}m | "
            f"HDG: {self.attitude_head:5.1f}° | "
            f"VEL: ({self.vx:4.1f}, {self.vy:4.1f}, {self.vz:4.1f}) | "
            f"TRIGGER: {self.trigger} | "
            f"CAMERA: {self.camera_mode} | "
            f"ZOOM: {self.last_zoom_list[self.last_zoom_index]} | "
            f"GIMBAL: {self.gimbal_pitch:5.1f}°"
        )