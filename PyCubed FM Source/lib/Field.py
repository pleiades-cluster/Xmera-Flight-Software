import time

class Field():

    def __init__(self,cubesat,debug):
        self.debug=debug
        self.impacketcount=0
        self.cubesat=cubesat
        self.cubesat.radio1.spreading_factor=8
        self.cubesat.radio1.tx_power=23
        self.cubesat.radio1.low_datarate_optimize=False
        self.cubesat.radio1.node=0xfb
        self.cubesat.radio1.destination=0xfa
        self.cubesat.radio1.receive_timeout=10
        self.cubesat.radio1.enable_crc=True
        if self.cubesat.radio1.spreading_factor>8:
            self.cubesat.radio1.low_datarate_optimize=True

    def fieldSide(self,msg,packlow,packhigh):

        pLow = str(packlow)   

        pHigh = str(packhigh)

        if packhigh < 10:
            pHigh = "00" + pHigh
        elif packhigh < 100:
            pHigh = "0" + pHigh
        else:
            pass

        if self.debug: print("Sending packet " + pLow + "/" + pHigh + ": ")
        self.cubesat.radio1.send("packet" + pLow + "/" + pHigh + ": " + msg, keep_listening=True)

        if self.debug: print("Listening for transmissions, " + str(self.cubesat.radio1.receive_timeout))
        heard_something = self.cubesat.radio1.await_rx(timeout=20)

        if heard_something:
            response = self.cubesat.radio1.receive(keep_listening=True)

            if response is not None :
                response_string = ''.join([chr(b) for b in response])
                if response_string == "True":
                    if self.debug: print("packet received")
                    if self.debug: print('msg: {}, RSSI: {}'.format(response_string,self.cubesat.radio1.last_rssi-137))
                    return True

                else:
                    if self.debug: print("something, but not what we were looking for: \"",response_string,"\"")
                    return False

    #Function to send Spresense and Face data over radio:
    def Data_Transmit(self, type, data, packets=6):
        if type == "Spresense":
            self.impacketcount=1
            logic=True
            for i in data:
                if self.debug: print(f"Sending packet ", self.impacketcount, "/", packets, ": ", i)
                logic=self.fieldSide(i,self.impacketcount,packets)
                self.impacketcount+=1
                if not logic:
                    if self.debug: print("I'm breaking from transmission!")
                    self.impacketcount-=1
                    return True
            self.impacketcount=0
            return False
        elif type == "Face":
            count=1
            for i in data:
                if self.debug: print(f"Sending face ", count, "/", packets, ": ", i)
                logic=self.fieldSide(str(i),count,packets)
                if not logic:
                    if self.debug: print("I'm breaking from transmission!")
                    return False
                count+=1
            return True
        elif type == "Error":
            count=1
            for i in data:
                if self.debug :print(f"Sending Error ", count, "/", packets, ": ", i)
                logic=self.fieldSide(i,count,packets)
                if not logic:
                    if self.debug: print("I'm breaking from transmission!")
                    return False
                count+=1
            return True
        else:
            if self.debug: print(f"No type with name: ", type, " nothing transmitted")
            return False
    
    def Beacon(self, msg):
        if self.debug: print("I am beaconing!")
        self.cubesat.radio1.send(msg)

    def __del__(self):
        if self.debug: print("Object Destroyed!")