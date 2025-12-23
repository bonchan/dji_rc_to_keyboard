import pygame
from time import sleep
from DJIFPVRemoteController3 import DJIFPVRemoteController3


pygame.init()

joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("No joysticks found.")
    exit()

# Initialize all joysticks
joysticks = []
for i in range(joystick_count):
    js = pygame.joystick.Joystick(i)
    js.init()
    print(f"Joystick {i}: {js.get_name()}")
    joysticks.append(js)


js = pygame.joystick.Joystick(0)
js.init()

controller = DJIFPVRemoteController3()

while True:
    controller.update_from_joystick(js)
    print(controller)
    sleep(0.101)
