##Xmera-Flight-Software
#The official flight software on PROVES Xmera
The C&DH board is utilizing an RP2040 which is a dual core microcontroller. The Goal is to utilize a form of parallelism via micropython libraries, and other hardware capabilites via circuitpython libraries

#PYCubed FM Source
This code is running on the Yearling Flight Model and inspires the Xmera software:
\begin{itemize}
  \item main.py supplies logic of how and when functions should execute
  \item Pycubed class which handles on-board hardware
  \item Functions class which handles major satellite utilities
  \item Big Data class which obtains all face data
  \item Other Adafruit hardware interface libraries
\end{itemize}
