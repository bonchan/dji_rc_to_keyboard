import json
import time
import asyncio
import websockets
import logging
from urllib.parse import urlparse, parse_qs

class WsServer:
    def __init__(self, host="localhost", port=8765, sim=None):
        self.host = host
        self.port = port
        self.sim = sim
        self.connected_clients = set()
        self.logger = logging.getLogger("OSDServer")
        self.server = None

    async def register(self, websocket):
        """Adds a new client (e.g., Chrome Extension) to the registry."""

        self.logger.info(f"register {websocket}")

        parsed_url = urlparse(websocket.request.path)
        query_params = parse_qs(parsed_url.query)

        # 2. Extract the values safely (remember they are stored in lists!)
        dock_sn = query_params.get('dock_sn', [None])[0]
        drone_sn = query_params.get('drone_sn', [None])[0]
        start_lon = query_params.get('start_lon', [None])[0]
        start_lat = query_params.get('start_lat', [None])[0]

        if self.sim:
            if start_lat:
                self.sim.lat = float(start_lat)
            if start_lon:
                self.sim.lng = float(start_lon)
            if drone_sn:
                self.sim.drone_sn = drone_sn
            if dock_sn:
                self.sim.dock_sn = dock_sn

            self.logger.info(f"Teleported Sim to Lat: {self.sim.lat}, Lon: {self.sim.lng}")

        self.connected_clients.add(websocket)
        self.logger.info(f"Client connected. Total: {len(self.connected_clients)}")
        try:
            await websocket.wait_closed()
        finally:
            self.connected_clients.remove(websocket)
            self.logger.info(f"Client disconnected. Total: {len(self.connected_clients)}")

    def _generate_payload(self, sim):
        """Maps the DroneSimulator state to the DJI OSD JSON format."""
        return {
          "version": "",
          "sub_biz_code": "",
          "to_category": "org_or_prj",
          "biz_code": "device_osd",
          "msg_trace_id": str(int(time.time())),
          "to": [
              "n",
              "n"
          ],
          "data": {
              "host": {
              "99-0-0": {
                  "gimbal_pitch": sim.gimbal_pitch,
                  "gimbal_roll": sim.gimbal_roll,
                  "gimbal_yaw": sim.gimbal_yaw,
                  "measure_target_altitude": sim.measure_target_altitude,
                  "measure_target_distance": sim.measure_target_distance,
                  "measure_target_error_state": sim.measure_target_error_state,
                  "measure_target_latitude": sim.measure_target_latitude,
                  "measure_target_longitude": sim.measure_target_longitude,
                  "payload_index": "99-0-0",
                  "thermal_current_palette_style": 0,
                  "thermal_gain_mode": 2,
                  "thermal_global_temperature_max": 20.3399600982666,
                  "thermal_global_temperature_min": 16.262903213500977,
                  "thermal_isotherm_lower_limit": -20,
                  "thermal_isotherm_state": 0,
                  "thermal_isotherm_upper_limit": 150,
                  "thermal_supported_palette_styles": [
                  0,
                  1,
                  2,
                  3,
                  5,
                  6,
                  8,
                  11,
                  12,
                  13
                  ],
                  "zoom_factor": sim.last_zoom_list[sim.last_zoom_index]
              },
              "activation_time": 1759422288,
              "attitude_head": sim.attitude_head,
              "attitude_pitch": sim.attitude_pitch,
              "attitude_roll": sim.attitude_roll,
              "battery": {
                  "batteries": [
                  {
                      "capacity_percent": 94,
                      "firmware_version": "37.03.01.39",
                      "high_voltage_storage_days": 107,
                      "index": 0,
                      "loop_times": 191,
                      "sn": "87UPN3DCA0001R",
                      "sub_type": 0,
                      "temperature": 21.8,
                      "type": 0,
                      "voltage": 24558
                  }
                  ],
                  "capacity_percent": 94,
                  "landing_power": 0,
                  "remain_flight_time": 0,
                  "remain_job_time": 65535,
                  "return_home_power": 0
              },
              "best_link_gateway": sim.dock_sn,
              "cameras": [
                  {
                  "camera_mode": sim.camera_mode,
                  "ir_metering_mode": 0,
                  "ir_metering_point": {
                      "temperature": 17.5997257232666,
                      "x": 0.5,
                      "y": 0.5
                  },
                  "ir_zoom_factor": 2,
                  "liveview_world_region": {
                      "bottom": 0.5597864985466003,
                      "left": 0.43633437156677246,
                      "right": 0.5617268681526184,
                      "top": 0.4332658052444458
                  },
                  "payload_index": sim.payload_index,
                  "photo_state": sim.trigger,
                  "photo_storage_settings": [
                      "vision"
                  ],
                  "record_time": 0,
                  "recording_state": 0,
                  "remain_photo_num": 13740,
                  "remain_record_duration": 0,
                  "screen_split_enable": False,
                  "wide_calibrate_farthest_focus_value": 28,
                  "wide_calibrate_nearest_focus_value": 61,
                  "wide_exposure_mode": 1,
                  "wide_exposure_value": 16,
                  "wide_focus_mode": 2,
                  "wide_focus_state": 0,
                  "wide_focus_value": 30,
                  "wide_iso": 6,
                  "wide_max_focus_value": 98,
                  "wide_min_focus_value": 0,
                  "wide_shutter_speed": 43,
                  "zoom_calibrate_farthest_focus_value": 28,
                  "zoom_calibrate_nearest_focus_value": 61,
                  "zoom_exposure_mode": 1,
                  "zoom_exposure_value": 16,
                  "zoom_factor": sim.last_zoom_list[sim.last_zoom_index],
                  "zoom_focus_mode": 2,
                  "zoom_focus_state": 0,
                  "zoom_focus_value": 30,
                  "zoom_iso": 6,
                  "zoom_max_focus_value": 98,
                  "zoom_min_focus_value": 0,
                  "zoom_shutter_speed": 43
                  }
              ],
              "country": "AR",
              "distance_limit_status": {
                  "distance_limit": 5000,
                  "is_near_distance_limit": 0,
                  "state": 0
              },
              "elevation": sim.alt,
              "fts_info": {
                  "fts_firmware_version": "",
                  "fts_sn": "",
                  "fts_status": 65535,
                  "fts_timestamp": 0,
                  "fts_valid_duration": 0,
                  "fts_verification_code": ""
              },
              "gear": 1,
              "height": 9999999.9,
              "height_limit": 300,
              "home_distance": sim.home_distance,
              "horizontal_speed": 0,
              "is_near_area_limit": 0,
              "is_near_height_limit": 0,
              "latitude": sim.lat,
              "longitude": sim.lng,
              "maintain_status": {
                  "maintain_status_array": [
                  {
                      "last_maintain_flight_sorties": 0,
                      "last_maintain_flight_time": 0,
                      "last_maintain_time": 0,
                      "last_maintain_type": 1,
                      "state": 0
                  },
                  {
                      "last_maintain_flight_sorties": 0,
                      "last_maintain_flight_time": 0,
                      "last_maintain_time": 0,
                      "last_maintain_type": 2,
                      "state": 0
                  },
                  {
                      "last_maintain_flight_sorties": 0,
                      "last_maintain_flight_time": 0,
                      "last_maintain_time": 0,
                      "last_maintain_type": 3,
                      "state": 0
                  }
                  ]
              },
              "mode_code": 0,
              "night_lights_state": 1,
              "obstacle_avoidance": {
                  "downside": 1,
                  "horizon": 1,
                  "upside": 1
              },
              "position_state": {
                  "gps_number": 25,
                  "is_fixed": 2,
                  "quality": 5,
                  "rtk_number": 30
              },
              "rc_lost_action": 2,
              "rid_state": False,
              "rth_altitude": 100,
              "storage": {
                  "total": 60382000,
                  "used": 9285000
              },
              "total_flight_distance": 2265524.336996492,
              "total_flight_sorties": 297,
              "total_flight_time": 407493.5308918096,
              "track_id": "",
              "vertical_speed": 0,
              "wind_direction": 0,
              "wind_speed": 0
              },
              "sn": sim.drone_sn
          },
          "timestamp": int(time.time() * 1000),
          "need_reply": False
          }

    async def broadcast_osd(self, sim):
        """Sends the OSD data to all connected websocket clients."""
        if not self.connected_clients:
            return

        message = json.dumps(self._generate_payload(sim))
        # Create a list of send tasks
        tasks = [asyncio.create_task(client.send(message)) for client in self.connected_clients]
        if tasks:
            await asyncio.wait(tasks)

    async def start(self):
        """Starts the websocket server task."""
        self.server = await websockets.serve(self.register, self.host, self.port)
        self.logger.info(f"OSD Server running on ws://{self.host}:{self.port}")