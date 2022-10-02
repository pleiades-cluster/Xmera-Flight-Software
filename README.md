## Xmera-Flight-Software
# The official flight software on PROVES Xmera
The C&DH board is utilizing an RP2040 which is a dual core microcontroller. The Goal is to utilize a form of parallelism via micropython libraries, and other hardware capabilites via circuitpython libraries

# ADCS Source
This code is what will run on the Raspberry Pi zero to perform calculations and execute operations to detumble the satellite. This code will also transfer sensor data to the C&DH for downlinking.

# C&DH Source
This code is intended to be the main operating code on the satellite, which will handle all mission operations and communications.

# EPS Source
This code is what will run on the PIC18F and will execute all basic battery functions to preserve and protect the battery, as well as translate basic battery information to the C&DH for Data handling and downlinking.

# PYCubed FM Source
This code is running on the Yearling Flight Model and inspires the Xmera software:
  * main.py supplies logic of how and when functions should execute
  * Pycubed class which handles on-board hardware
  * Functions class which handles major satellite utilities
  * Big Data class which obtains all face data
  * Other Adafruit hardware interface libraries
