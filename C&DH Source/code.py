'''
In this method the PyCubed will wait a pre-allotted loiter time before proceeding to execute
main. This loiter time is to allow for a keyboard interupt if needed. 
'''

import time
import neopixel
import board
import microcontroller
import supervisor

print("Xmera Flight Software executing in:")
loiter_time = 10

try:
    try:
        led = neopixel.NeoPixel(board.GP18, 1, brightness = 0.2, pixel_order = neopixel.GRBW)
        led[0] = (0,0,0)
        
        purple = (200, 8, 200)
        led_off = (0,0,0)
        
    except Exception as e:
        print(e)
        
    for step in range(0,loiter_time):
        
        led[0] = purple
        time.sleep(0.5)
        led[0] = led_off
        time.sleep(0.5)
        
        print(f"{loiter_time-step} seconds")
        
    led.deinit()
    
    import main

except Exception as e:    
    print(e)
    time.sleep(5)
    microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
    supervisor.reload()