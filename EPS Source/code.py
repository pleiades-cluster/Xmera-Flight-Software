'''
This is the code.py for the EPS board, in which the board will loiter for 2 minutes before executing the main code. 
'''
########################################################
##                       TO DO:                       ##
## -find out how long to actually loiter for          ##
## -synchronize loitering with CDH                    ##
## -Can send control signal in main for CDH to know   ##
##  ... when to wake up                               ##
########################################################

import time
import board
import microcontroller
import neopixel

print("Hello World!")
loiter_time = 15
led = neopixel.NeoPixel(board.GP18, 1, brightness=0.2, pixel_order=neopixel.GRB)
led[0] = (0,0,0)
try:
        
    for step in range(0,loiter_time):
        
        led[0] = purple
        time.sleep(0.5)
        led[0] = led_off
        time.sleep(0.5)
        
        print(f"Executing code in... {loiter_time-step} seconds")
        
    led.deinit()
    
    import main

except Exception as e:    
    print(e)
    time.sleep(5)
    microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
    microcontroller.reset()