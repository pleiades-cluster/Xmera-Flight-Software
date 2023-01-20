'''
This is the class that contains all of the functions for our CubeSat. 
We pass the cubesat object to it for the definitions and then it executes 
our will.
Authours: Michael, Nicole
'''
import time
import Big_Data
import eps
import alarm
import Field
import gc

class functions:

    def __init__(self,cubesat):
        print("Initializing Functionalities")
        self.cubesat = cubesat
        self.debug = cubesat.debug
        self.Errorcount=0
        self.packetstring=[]
        self.facestring=[]
        self.last_battery_temp = 20
        self.image_packets=0
        self.impacketsofar=0
        self.hasImage=False
        self.face_data_baton = False
        self.cubesat.all_faces_on()
    
    '''
    Satellite Management Functions
    '''
    def battery_heater(self):
        """
        Battery_Heater Function. Called to turn on the battery heater for 30s.
        NOTE: we may want to add functionality to see if thermocouple has been reliable
        if a particular nvm flag gets flipped, then we may want to run heater on a timer
        """

        self.cubesat.all_faces_on()
        
        self.face_toggle("Face1",True)
        a=Big_Data.AllFaces(self.debug)
        a.Get_Thermo_Data()
        corrected_temp= a.Face1.couple[0]-a.Face1.couple[2]
        
        if corrected_temp < self.cubesat.NORMAL_BATT_TEMP:
            
            self.cubesat.heater_on()
            for _ in range (0,30):
                corrected_temp= a.Face1.couple[0]-a.Face1.couple[2]
                if self.debug: print(f"Uncorrected: {a.Get_Thermo_Data()}")
                if self.debug: print(f"Corrected: {corrected_temp}")
                time.sleep(1) 
            self.cubesat.heater_off()
            
            del a
            return True
        else: 
            if self.debug: print("Battery is already warm enough")
            del a
            return False
    
    def current_check(self):
        return self.cubesat.current_draw
    
    def test_faces(self):    
        self.cubesat.all_faces_on()
        a = self.all_face_data()
        
        self.last_battery_temp= a[1][5][0]-a[1][5][2]
        
        #Iterate through a and determine if any of the values are None
        #Add a counter to keep track of which iternation we are on
        count = 0 
        for face in a:
            if len(face) == 0:
                if self.debug: print("Face " + str(count) + " is None")
                self.cubesat.hardware[f'Face{count}'] = False
                count += 1
            else:
                self.cubesat.hardware[f'Face{count}'] = True
                count += 1
        
        if self.debug: print(self.cubesat.hardware)

    '''
    Radio Functions
    '''  
    def send(self,msg):
        """Calls the RFM9x to send a message. Currently only sends with default settings.

        Args:
            msg (String,Byte Array): Pass the String or Byte Array to be sent. 
        """
        self.field = Field.Field(self.cubesat,self.debug)
        self.field.fieldSide(str(msg),1,1)
        if self.debug: print(f"Sent Packet: ",msg)
        del self.field

    def beacon(self):
        """Calls the RFM9x to send a beacon. """
        lora_beacon = "KN6NAQ Hello I am Yearling! I am in: " + str(self.cubesat.power_mode) +" power. V_Batt = " + str(self.cubesat.battery_voltage) + ". IHBPFJASTMNE! KN6NAQ"
        self.field = Field.Field(self.cubesat,self.debug)
        self.field.Beacon(lora_beacon)
        del self.field

    def state_of_health(self):
            
        self.test_faces()
            
        #Dictionary of state information 
        self.state_list = [
            f"PM:{self.cubesat.power_mode}",
            f"VB:{self.cubesat.battery_voltage}",
            f"IC:{self.cubesat.charge_current}",
            f"TB:{self.last_battery_temp}", 
            f"ID:{self.cubesat.current_draw}",
            f"VS:{self.cubesat.system_voltage}",
            f"MT:{self.cubesat.micro.cpu.temperature}",
        ]
        

        self.field = Field.Field(self.cubesat,self.debug)
        self.field.Beacon("Yearling State of Health 1/2" + str(self.state_list))
        self.field.Beacon("2/2" + str(self.cubesat.hardware))
        del self.field
    
    def send_image(self):
        """Calls the data transmit function from the field class
        """
        self.field = Field.Field(self.cubesat,self.debug)
        if self.impacketsofar > 0:
            if self.debug: print("continuing to send previous image")
        else:
            if self.debug: print("Sending a new image")
        self.hasImage=self.field.Data_Transmit("Spresense", self.packetstring[self.impacketsofar:], self.image_packets-self.impacketsofar)
        self.impacketsofar = self.field.impacketcount
        del self.field
        if not self.hasImage: return True
        else: return False

    def send_face(self):
        """Calls the data transmit function from the field class
        """
        self.field = Field.Field(self.cubesat,self.debug)
        if self.debug: print("Sending Face Data")
        self.field.Data_Transmit("Face", self.facestring, 6)
        del self.field
    
    def send_face_data_small(self):
        print("Trying to get the data! ")
        data = self.all_face_data()
        i = 0
        try:
            for face in data:
                if self.debug: print(face)
                self.cubesat.radio1.send("Face Data: " + str(i) + " " + str(face))
                i+=1
            return True
        except Exception as e:
            print(e)
            #self.cubesat.all_faces_off()
            return False
    
    def listen(self):

        #This just passes the message through. Maybe add more functionality later. 
        self.cubesat.radio1.receive_timeout=10
        received = self.cubesat.radio1.receive()
        time.sleep(5)
        if received is not None:
            if self.debug: print(f"Recieved Packet: ",received)
            cdh.message_handler(self.cubesat, received)
            return True
        
        return False

        
    
    '''
    Big_Data Face Functions
    '''  
    def face_toggle(self,face,state):
        
        on_off = not state 
        
        if face == "Face0": self.cubesat.zPosFet.value = on_off      
        elif face == "Face1": self.cubesat.zNegFet.value = on_off
        elif face == "Face2": self.cubesat.yPosFet.value = on_off      
        elif face == "Face3": self.cubesat.xNegFet.value = on_off           
        elif face == "Face4": self.cubesat.xPosFet.value = on_off          
        elif face == "Face5": self.cubesat.yNegFet.value = on_off

    '''
    def face_data(self,face,data_type):
        
        if face == "Face0": 
            self.face_toggle(face,True)
            
        elif face == "Face1": self.cubesat.zNegFet.value = on_off
        elif face == "Face2": self.cubesat.yPosFet.value = on_off      
        elif face == "Face3": self.cubesat.xNegFet.value = on_off           
        elif face == "Face4": self.cubesat.xPosFet.value = on_off          
        elif face == "Face5": self.cubesat.yNegFet.value = on_off
        return data
    '''
    
    def all_face_data(self):
        
        #self.cubesat.all_faces_on()
        a = Big_Data.AllFaces(self.debug)
        
        self.facestring = a.Face_Test_All()
        
        del a
        #self.cubesat.all_faces_off()
        
        return self.facestring
    
    def get_imu_data(self):
        
        self.cubesat.all_faces_on()
        a = Big_Data.AllFaces(self.debug)
        
        data = a.Get_IMU_Data()
        
        del a
        #self.cubesat.all_faces_off()
        
        return data
    
    '''
    Spresense Functions
    '''  
    #Function to take a 480p picture from the Spresense
    def get_picture(self):

        if self.debug: print("Initiating Spresense")
        print(gc.mem_free())
        #Activate the Spresense and wait for the UART to be ready
        self.cubesat.Spresense_on()
        time.sleep(1)
        self.cubesat.uart.reset_input_buffer()
        
        #Initialize helper variables
        count=0
        data_string=""
        self.packetstring=[]
        self.image_packets=0
        self.cubesat.uart.timeout=5
        self.cubesat.uart.write(bytearray("yes"))
        data = self.cubesat.uart.read(200)  # read 100 hex bytes
        while data is None and count < 5:
            self.cubesat.uart.write(bytearray("yes"))
            data = self.cubesat.uart.read(200)  # read 100 hex bytes
            if data is not None:
                time.sleep(.5)
                self.cubesat.uart.write(bytearray("True"))
            count=count+1
        count=0
        self.cubesat.uart.write(bytearray("True"))
        while count<7:
            #Reading the data from the UART buffer
            try:
                while data is not None:
                    #Blocking while loop to continue reading the data until no new data is sent
                    if self.debug: print("Packet " + str(self.image_packets+1) + ":")
                    count=0
                    self.image_packets+=1
                    
                    # convert bytearray to string
                    data_string = ''.join([chr(b) for b in data])
                    self.packetstring.append(data_string)
                    if self.debug: print(data_string, end="")
                    print(gc.mem_free())
                    #if self.debug: print("size of list: ", self.packetstring.__sizeof__)
                    
                    #Read new set of data
                    data = self.cubesat.uart.read(200)  # read 100 hex bytes
                    self.cubesat.uart.reset_input_buffer()
                    
                    #Ack Message
                    if self.debug: print("\nI wrote back")
                    self.cubesat.uart.write(bytearray("True"))

            except Exception as e:
                print('Picture receive error:',e)
                self.packetstring=[]
                self.image_packets=0

            if self.debug: print("missed packet")
            self.cubesat.uart.write(bytearray("True"))
            time.sleep(1)
            count+=3 #While loop escape in case of no data 
            data = self.cubesat.uart.read(200)  # read 100 hex bytes

        self.cubesat.uart.write(bytearray("Done"))

        self.cubesat.Spresense_off()

        if self.debug: print(*self.packetstring,sep='')

        return self.packetstring

    '''
    Logging Functions
    '''  
    def log_face_data(self,data):
        
        if self.debug: print("Logging Face Data")
        try:
                self.cubesat.Face_log(data)
        except:
            try:
                self.cubesat.new_file(self.cubesat.Facelogfile)
            except Exception as e:
                print('SD error:',e)
        
    def log_error_data(self,data):
        
        if self.debug: print("Logging Error Data")
        try:
                self.cubesat.log(data)
        except:
            try:
                self.cubesat.new_file(self.cubesat.logfile)
            except Exception as e:
                print('SD error:',e)
    
    def log_image_data(self,data):
        
        try:
            if self.debug: print("Here is the image")
            if self.debug: print(*data, sep='')
            
            try:
                    self.cubesat.Image_log(data)
            except:
                try:
                    self.cubesat.new_file(self.cubesat.Imagelogfile)
                except Exception as e:
                    print('SD error:',e)
        except Exception as e:
            print('Print error:',e)
    
    '''
    Misc Functions
    '''  
    #Goal for torque is to make a control system 
    #that will adjust position towards Earth based on Gyro data
    def torque(self):
        data=self.get_imu_data()
        self.cubesat.all_faces_on()
        a = Big_Data.AllFaces(self.debug)
        #I think sequences should be different to bring us back to zero from either side
        #durations should be different based on how far off the angle is
        #durations should NOT be constant
        if data[0] < 0:
            a.sequence=181
            a.drvz_actuate(data[0]/2)
        elif data[0] > 0:
            a.sequence=181
            a.drvz_actuate(data[0]/2)
        
        if data[1] < 0:
            a.sequence=181
            a.drvx_actuate(data[1]/2)
        elif data[1] > 0:
            a.sequence=181
            a.drvx_actuate(data[1]/2)

        if data[2] < 0:
            a.sequence=181
            a.drvy_actuate(data[2]/2)
        elif data[2] > 0:
            a.sequence=181
            a.drvy_actuate(data[2]/2)

        del a
        #self.cubesat.all_faces_off()

        return True
    
    def Short_Hybernate(self):
        if self.debug: print("Short Hybernation Coming UP")
        gc.collect()
        #all should be off from cubesat powermode
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 120)#change to 2 min when not testing
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)
        return True
    
    def Long_Hybernate(self):
        if self.debug: print("LONG Hybernation Coming UP")
        gc.collect()
        #all should be off from cubesat powermode
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 600)
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)
        return True
    