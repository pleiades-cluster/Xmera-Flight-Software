'''
This is the class that contains all of the functions for our CubeSat. 
We pass the cdh object to it for the definitions and then it executes 
our will.
Authours: Michael, Nicole
'''
from debugcolor import co
import time
import Big_Data
import command
import alarm
import Field
import gc

######################## TO DO: ###############################
#
###############################################################

class functions:

    def __init__(self,cdh):
        self.cdh = cdh
        self.debug = cdh.debug
        self.debug_print("Initializing Functionalities...")
        self.Errorcount=0
        self.last_battery_temp=20
        self.facestring=[]
        self.hasImage=False
        self.face_data_baton = False
        self.cdh.all_faces_on()
        self.debug_print("complete!")
    
    def debug_print(self,statement):
        if self.debug:
            print(co("[FUNCTIONS]"+statement,"green","bold"))
    
    '''
    Satellite Management Functions
    '''
    
    def test_faces(self):    
        self.cdh.all_faces_on()
        a = self.all_face_data()
        
        #Iterate through a and determine if any of the values are None
        #Add a counter to keep track of which iternation we are on
        count = 0 
        for face in a:
            if len(face) == 0:
                self.debug_print("Face " + str(count) + " is None")
                self.cdh.hardware[f'Face{count}'] = False
                count += 1
            else:
                self.cdh.hardware[f'Face{count}'] = True
                count += 1
        
        self.debug_print(str(self.cdh.hardware))

    '''
    Radio Functions
    '''  
    def send(self,msg):
        """Calls the RFM9x to send a message. Currently only sends with default settings.

        Args:
            msg (String,Byte Array): Pass the String or Byte Array to be sent. 
        """
        if self.cdh.hardware['Radio1']:
            self.field = Field.Field(self.cdh,self.debug)
            self.field.fieldSide(str(msg),1,1)
            self.debug_print(f"Sent Packet: ",msg)
            del self.field

    def beacon(self):
        """Calls the RFM9x to send a beacon. """
        if self.cdh.hardware['Radio1']:
            lora_beacon = "KN6NAQ Hello I am Xmera! I am in: " + str(self.cdh.PowerMode) +" power. V_Batt = " + str(self.cdh.battery_voltage) + ". AMAITTRTD! KN6NAQ"
            self.field = Field.Field(self.cdh,self.debug)
            self.field.Beacon(lora_beacon)
            del self.field

    def state_of_health(self):
            
        self.test_faces()
            
        #Dictionary of state information 
        self.state_list = [
            f"PM:{self.cdh.PowerMode}",
            f"VB:{self.cdh.battery_voltage}",
            f"IC:{self.cdh.charge_current}",
            f"TB:{self.last_battery_temp}", 
            f"MT:{self.cdh.micro.cpu.temperature}",
        ]

        self.debug_print(str(self.state_list))
        
        if self.cdh.hardware['Radio1']:
            self.field = Field.Field(self.cdh,self.debug)
            self.field.Beacon("Yearling State of Health 1/2" + str(self.state_list))
            self.field.Beacon("2/2" + str(self.cdh.hardware))
            del self.field

    def send_face(self):
        """Calls the data transmit function from the field class
        """
        if self.cdh.hardware['Radio1']:
            self.field = Field.Field(self.cdh,self.debug)
            self.debug_print("Sending Face Data")
            self.field.Data_Transmit("Face", self.facestring, 6)
            del self.field
    
    def get_and_push_face_data(self):
        if self.cdh.hardware['Radio1']:
            self.debug_print("Trying to get the data! ")
            data = self.all_face_data()
            i = 0
            try:
                for face in data:
                    self.debug_print(face)
                    self.cdh.radio1.send("Face Data: " + str(i) + " " + str(face))
                    i+=1
                return True
            except Exception as e:
                self.debug_print(e)
                #self.cdh.all_faces_off()
                return False
    
    def listen(self):
        if self.cdh.hardware['Radio1']:
            #This just passes the message through. Maybe add more functionality later. 
            self.cdh.radio1.receive_timeout=10
            received = self.cdh.radio1.receive()
            time.sleep(5)
            if received is not None:
                self.debug_print(f"Recieved Packet: ",received)
                command.message_handler(self.cdh, received)
                return True
            
            return False

        
    
    '''
    Big_Data Face Functions
    '''  
    
    def all_face_data(self):
        
        #self.cdh.all_faces_on()
        a = Big_Data.AllFaces(self.debug)
        
        self.facestring = a.Face_Test_All()
        
        del a
        #self.cdh.all_faces_off()
        
        return self.facestring
    
    def get_imu_data(self):
        
        self.cdh.all_faces_on()
        a = Big_Data.AllFaces(self.debug)
        
        data = a.Get_IMU_Data()
        
        del a
        #self.cdh.all_faces_off()
        
        return data

    '''
    Logging Functions
    '''  
    def log_face_data(self,data):
        
        self.debug_print("Logging Face Data")
        try:
                self.cdh.Face_log(data)
        except:
            try:
                self.cdh.new_file(self.cdh.Facelogfile)
            except Exception as e:
                self.debug_print('SD error:',e)
        
    def log_error_data(self,data):
        
        self.debug_print("Logging Error Data")
        try:
                self.cdh.log(data)
        except:
            try:
                self.cdh.new_file(self.cdh.logfile)
            except Exception as e:
                self.debug_print('SD error:',e)
    
    '''
    Misc Functions
    '''  
    #Goal for torque is to make a control system 
    #that will adjust position towards Earth based on Gyro data
    def Detumble(self):
        data=self.get_imu_data()
        self.cdh.all_faces_on()
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
        #self.cdh.all_faces_off()

        return True
    
    def Short_Hybernate(self):
        self.debug_print("Short Hybernation Coming UP")
        gc.collect()
        #all should be off from cdh powermode
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 120)#change to 2 min when not testing
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)
        return True
    
    def Long_Hybernate(self):
        self.debug_print("LONG Hybernation Coming UP")
        gc.collect()
        #all should be off from cdh powermode
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 600)
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)
        return True
    