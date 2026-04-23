from src.utils.logger_setup import setup_logger
import time
import argparse
import asyncio
from aiohttp import web
from src.remote_controller.dji_rc3 import DJIRC3
from src.remote_controller.dji_rcN1 import DJIRCN1
from src.remote_controller.dji_m300 import DJIM300
from src.remote_controller.base_rc import RCConnectionError

from src.simulator.drone_simulator import DroneSimulator
from src.simulator.ws_server import WsServer


PUBLISH_INTERVAL = 0.01

async def main_loop(model_choice):
    logger = setup_logger(None, 'Main')
    logger.info(f"--- DJI Universal Interface | Target: {model_choice} ---")

    sim = DroneSimulator(lat=0, lng=0, alt=2.0, drone_sn='DRONE_SN', dock_sn='DOCK_SN')
    ws_server = WsServer(host="localhost", port=8765, sim=sim)
    await ws_server.start()

    async def get_osd(request):
        # Customize this payload based on what attributes `sim` has
# "code": 0,
#     "message": "OK",
#     "data": {
#         "list": [

        topology = {
            "host": {
                "device_sn": sim.drone_sn,
                "device_state":{
                    "longitude": sim.lng,
                    "latitude": sim.lat,
                    "elevation": sim.alt,
                    "height": sim.alt,
                    "cameras": [
                        {
                            "payload_index": sim.payload_index,
                            "zoom_factor": sim.last_zoom_list[sim.last_zoom_index]
                        }
                    ],
                    sim.payload_index: {
                        "gimbal_yaw": sim.attitude_head,
                        "gimbal_pitch": sim.gimbal_pitch,
                    }
                },
            },
            "parents": [
                {
                    "device_sn": sim.dock_sn,
                }
            ]

        }


        payload = {
            "code": 0,
            "message": "OK" if rc and rc.is_connected else "ERROR",
            "data": {
                "list": [topology]
            }
        }
        return web.json_response(payload)
    
    app = web.Application()
    app.router.add_get('/api/osd', get_osd)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080) # Serving on port 8080
    await site.start()
    logger.info("HTTP Endpoint running at http://localhost:8080/api/osd")

    last_osd_time = time.time()

    rc = None
    retry_limit = 15

    for retry in range(retry_limit):
        try:
            if model_choice == 'RC3':
                rc = DJIRC3(joystick_index=0, deadzone_threshold_movement=0.3, deadzone_threshold_elevation=0.6, deadzone_threshold_tilt=0.1)
            elif model_choice == 'M300':
                rc = DJIM300()
            elif model_choice == 'N1':
                rc = DJIRCN1()
            
            # If we reach this line, constructor succeeded
            logger.info(f"Successfully connected to {model_choice}!")
            break 
            
        except RCConnectionError as e:
            rc = None
            logger.info(f"Retrying... [{retry}/{retry_limit}] {e}")
            time.sleep(1)

    # 3. Universal loop
    try:
        logger.info("Streaming data. Press Ctrl+C to stop.")
        while True:
            if not rc.is_connected:
                logger.info("[!!!] CONTROLLER DISCONNECTED [!!!]")
                break

            if not rc.update(): continue

            sim.update(rc)

            current_time = time.time()
            if current_time - last_osd_time >= PUBLISH_INTERVAL:
                await ws_server.broadcast_osd(sim)
                last_osd_time = current_time
                print(f"[OSD Sent] {sim}")
                # print(rc)

            await asyncio.sleep(0.01)
            
            time.sleep(0.01) # ~100Hz update rate

    except KeyboardInterrupt:
        logger.info("User interrupted. Closing connection...")
    finally:
        rc.close()
        logger.info("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DJI RC Interface")
    
    # Define the --model flag
    parser.add_argument(
        '--model', 
        type=str, 
        default='RC3', 
        choices=['RC3', 'N1', 'M300'],
        help='Remote controller model to use (default: RC3)'
    )
    
    args = parser.parse_args()

    # Standard way to run an async main in Python 3.7+
    try:
        asyncio.run(main_loop(args.model))
    except KeyboardInterrupt:
        pass