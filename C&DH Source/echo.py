from CDH import cdh
import time

yagiMode = True
#testMsg = "According to all known laws of aviation, there is no way a bee should be able to fly."
#testMsg = "Its over Anakin I have the high ground!"
#testMsg = "I have brought peace, freedom, justice, and security to my new empire. Your new empire!?"
#testMsg = "Hello There!"
testMsg = "ahhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh"

cdh.radio1.spreading_factor=8
cdh.radio1.tx_power=13
cdh.radio1.low_datarate_optimize=False
cdh.radio1.node=0xfb
cdh.radio1.destination=0xfa
cdh.radio1.receive_timeout=15
cdh.radio1.enable_crc=False

if cdh.radio1.spreading_factor>8:
    cdh.radio1.low_datarate_optimize=True

def yagiSide(): 
    print("Listening for transmissions, 5s")
    heard_something = cdh.radio1.await_rx(timeout=10)

    if heard_something:
        response = cdh.radio1.receive(keep_listening=True)

        if response is not None:
            print("packet received")
            print('msg: {}, RSSI: {}'.format(response,cdh.radio1.last_rssi-137))

            

            cdh.radio1.send('Echo:{}'.format(cdh.radio1.last_rssi-137))
            print("Echo sent")
            time.sleep(1)

    time.sleep(2)
    
def cop_yagiSide(): 
    print("Listening for transmissions, 5s")
    heard_something = cdh.radio1.await_rx(timeout=10)

    if heard_something:
        response = cdh.radio1.receive(keep_listening=True)

        if response is not None:
            print("packet received")
            print('msg: {}, RSSI: {}'.format(response,cdh.radio1.last_rssi-137))

            

            cdh.radio1.send('Echo:{}'.format(cdh.radio1.last_rssi-137))
            print("Echo sent")
            time.sleep(1)

    time.sleep(2)

def fieldSide():
    print("Sending test message:")
    cdh.radio1.send(testMsg + " SF: " + str(cdh.radio1.spreading_factor), keep_listening=True)

    print("Listening for transmissions, 5s")
    heard_something = cdh.radio1.await_rx(timeout=2)

    if heard_something:
        response = cdh.radio1.receive(keep_listening=True)

        if response is not None:
            print("packet received")
            print('msg: {}, RSSI: {}'.format(response,cdh.radio1.last_rssi-137))

    time.sleep(2)
    
def banger():
    print("Banging away")
    
    cdh.radio1.send(testMsg + " SF: " + str(cdh.radio1.spreading_factor))
    
    response = cdh.radio1.receive(keep_listening=True)
    
    if response is not None:
        print("packet received")
        print('msg: {}, RSSI: {}'.format(response,cdh.radio1.last_rssi-137))

    
    time.sleep(2)


while True:
    
    #banger()
    
    if yagiMode: 
        yagiSide()
    else: 
        fieldSide()