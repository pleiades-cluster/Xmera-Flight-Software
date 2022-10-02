'''
This class creates an object for each face of Yearling. 

Authors: Antony Macar, Michael Pham, Nicole Maggard
Updated July 26, 2022 
v1.1
''' 
from debugcolor import co
import time
import board
import busio
import adafruit_apds9960.apds9960
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_mcp9808
import adafruit_tca9548a
import adafruit_lis3mdl
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
import adafruit_drv2605
import adafruit_mcp9600

try:
    # Create I2C bus as normal
    i2c2 = busio.I2C(board.GP27, board.GP26)
except Exception as e:
    i2c2=None
    print(f'I2C Initialization error: ',e)

# Create the TCA9548A object and give it the I2C2 bus
tca = adafruit_tca9548a.TCA9548A(i2c2)

class Face:

    def __init__(self, Add, Pos, debug_state):
        self.address = Add
        self.position = Pos
        self.debug= debug_state

        #Sensor List Contains Expected Sensors Based on Face
        self.senlist = []
        self.datalist = [] #[temp light mag accel gyro motordriver thermo]
        if Pos == "x+":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
            self.senlist.append("DRV")
        elif Pos == "x-":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
            self.senlist.append("DRV")
        elif Pos == "y+":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
            self.senlist.append("MAG")
            self.senlist.append("IMU")
        elif Pos == "y-":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
            self.senlist.append("MAG")
            self.senlist.append("IMU")
        elif Pos == "z-":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
            self.senlist.append("MAG")
            self.senlist.append("IMU")
            self.senlist.append("DRV")
            self.senlist.append("COUPLE")
        elif Pos == "z+":
            self.senlist.append("MCP")
            self.senlist.append("ADPS")
        else:
            self.debug_print("[ERROR] Please input a propper face")

        #This sensors set contains information as to whether sensors are actually working
        self.sensors = { 
            'MCP':      False,
            'ADPS':     False, 
            'MAG':      False,
            'IMU':      False, 
            'DRV':      False,
            'COUPLE':   False, 
        }

    def debug_print(self,statement):
        if self.debug:
            print(co("[BIG_DATA]"+statement,"orange","bold")) 

    @property
    def debug_value(self):
        return self.debug
    
    @debug_value.setter
    def debug_value(self,value):
        self.debug=value    

    # function to initialize all the sensors on that face        
    def Sensorinit(self,senlist,address):

        #Initialize Temperature Sensor
        if "MCP" in senlist:
            try:
                self.mcp = adafruit_mcp9808.MCP9808(tca[address])
                self.sensors['MCP'] = True
                self.debug_print('[ACTIVE][Temperature Sensor]')
            except Exception as e:
                self.debug_print('[ERROR][Temperature Sensor]',e)

        #Initialize Light Sensor
        if "ADPS" in senlist:
            try:
                self.light1 = adafruit_apds9960.apds9960.APDS9960(tca[address])
                self.light1.enable_color =True
                self.light1.enable_proximity = True
                self.sensors['ADPS'] = True
                self.debug_print('[ACTIVE][Light Sensor]')
            except Exception as e: 
                self.debug_print('[ERROR][Light Sensor]',e)
        
        #Initialize Magnetometer
        if "MAG" in senlist:            
            try:
                self.mag1 = adafruit_lis3mdl.LIS3MDL(tca[address])
                self.sensors['MAG'] = True
                self.debug_print('[ACTIVE][Magnetometer]')
            except Exception as e:
                self.debug_print('[ERROR][Magnetometer]',e)
        
        #Initialize IMU
        if "IMU" in senlist:
            try:
                self.imu = LSM6DSOX(tca[address])
                self.sensors['IMU'] = True
                self.debug_print('[ACTIVE][IMU]')
            except Exception as e: 
                self.debug_print('[ERROR][IMU]',e)

        #Initialize Motor Driver
        if "DRV" in senlist:
            try:
                self.drv1 = adafruit_drv2605.DRV2605(tca[address])
                self.sensors['DRV'] = True
                self.debug_print('[ACTIVE][Motor Driver]')
            except Exception as e:
                self.debug_print('[ERROR][Motor Driver]',e)
                
        #Initialize Thermocouple
        if "COUPLE" in senlist:
            try:
                self.couple1 = adafruit_mcp9600.MCP9600(tca[address]) 
                self.sensors['COUPLE'] = True
                self.debug_print('[ACTIVE][Thermocouple]')
            except Exception as e:
                self.debug_print('[ERROR][Thermocouple]',e)

        self.debug_print('Initialization Complete')

    #Meta Info Getters 
    @property #Gives what sensors should be present
    def senlist_what(self): 
        return self.senlist 
    
    @property #Givens what sensors are actually present 
    def active_sensors(self): 
        return self.sensors

    #Sensor Data Getters 

    @property #Temperature Data Getter
    def temperature(self): 
        if self.sensors['MCP']:
            return self.mcp.temperature
        else:
            self.debug_print('[WARNING]Temperature sensor not initialized')

    @property #Light Sensor Color Data Getter
    def color_data(self): 
        if self.sensors['ADPS']:
            r1, g1, b1, c1 = self.light1.color_data
            return r1, g1, b1, c1
        else:
            self.debug_print('[WARNING]Light sensor not initialized')

    @property #Magnetometer Getter 
    def mag(self): 
        if self.sensors['MAG']:
            mag_x, mag_y, mag_z = self.mag1.magnetic
            return mag_x, mag_y, mag_z#Note return is a tuple 
        else:
            self.debug_print('[WARNING]Magnetometer not initialized')  

    @property #IMU Accelerometer Getter
    def accel(self):
        if self.sensors['IMU']:
            return self.imu.acceleration
        else:
            self.debug_print('[WARNING]IMU not initialized')   
    
    @property #IMU Gyroscope Getter
    def gyro(self):
        if self.sensors['IMU']:
            return self.imu.gyro
        else:
            self.debug_print('[WARNING]IMU not initialized')  

 
    def drv_actuate(self, duration): 
        if self.sensors['DRV']:
            self.debug_print('Actuating Sequence')
            self.debug_print("Playing effect #{0}".format(self.drv))
            if self.debug & self.sensors['MAG']: self.debug_print("X:%.2f, Y: %.2f, Z: %.2f uT"%(self.mag))
            self.drv1.play()
            if self.debug & self.sensors['MAG']: self.debug_print("X:%.2f, Y: %.2f, Z: %.2f uT"%(self.mag))
            time.sleep(duration)
            if self.debug & self.sensors['MAG']: self.debug_print("X:%.2f, Y: %.2f, Z: %.2f uT"%(self.mag))
            self.drv1.stop()
            if self.debug & self.sensors['MAG']: self.debug_print("X:%.2f, Y: %.2f, Z: %.2f uT"%(self.mag))
            self.debug_print('Actuation Complete')
        else: 
            self.debug_print('[WARNING]Motor driver not initialized')

    @property #driver sequence Getter 
    def drv(self): 
        if self.sensors['DRV']:
            return self.drv1.sequence[0]
        else:
            self.debug_print('[WARNING]Motor driver not initialized')

    @drv.setter #setter
    def drv(self, sequence): 
        if self.sensors['DRV']:
            try:
                self.debug_print('Encoding Sequence')
                self.drv1.sequence[0] = adafruit_drv2605.Effect(sequence)
                self.debug_print('Complete')
            except Exception as e:
                self.debug_print('[ERROR][Motor Driver]',e)
        else: 
            self.debug_print('[WARNING]Motor driver not initialized')


    @property #Thermocouple Getter 
    def couple(self): 
        if self.sensors['COUPLE']:
            amb = self.couple1.ambient_temperature
            tip = self.couple1.temperature
            dif = self.couple1.delta_temperature
            return amb, tip, dif #Note return is a tuple 
        else:
            self.debug_print('[WARNING]Thermocouple not initialized')  



    #Function to test all sensors that should be on each face. 
    #Function takes number of tests "num" and polling rate in hz "rate"
    def test_all(self, num, rate): 
        self.datalist=[]
        self.debug_print('Expected Sensors: ', self.senlist_what)
        self.debug_print('Initialized Sensors: ', self.active_sensors)
        time.sleep(1) #Remove later for performance boost! 
        self.debug_print('Initializing Test')

        for i in range(num): 

            self.debug_print('Test Number: ', i+1, ' /', num)

            #Test Temperature Sensor
            self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if ("MCP" in self.senlist) and (self.sensors.get("MCP") == True):
                try:
                    self.debug_print('Temperature Sensor')
                    self.debug_print('Face Temperature: ', self.temperature)
                    self.datalist.append(self.temperature)
                except Exception as e:
                    self.debug_print('[ERROR][Temperature Sensor]',e)
            else:
                self.debug_print('[ERROR]Temperature Sensor Failure')
                
            self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            #Test Light Sensor
            if ("ADPS" in self.senlist) and (self.sensors.get('ADPS') == True ):
                try:
                    self.debug_print('Light Sensor')
                    self.debug_print(self.color_data)
                    self.datalist.append(self.color_data)
                except Exception as e: 
                    self.debug_print('[ERROR][Light Sensor]',e)
            else:
                self.debug_print('[ERROR]Light Sensor Failure')
                
            self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            #Test Magnetometer
            if ("MAG" in self.senlist) and (self.sensors.get('MAG') == True ):            
                try:
                    self.debug_print('Magnetometer')
                    self.debug_print("X:%.2f, Y: %.2f, Z: %.2f uT"%(self.mag))
                    self.datalist.append(self.mag)
                except Exception as e:
                    self.debug_print('[ERROR][Magnetometer]',e)
                self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~') 
            elif self.position == "x+" or self.position == "x-" or self.position == "z+":
                pass
            else:
                self.debug_print('[Error]Magnetometer Failure')
                
            #Test IMU
            if ("IMU" in self.senlist) and (self.sensors.get('IMU') == True ):            
                try:
                    self.debug_print('IMU')
                    self.debug_print("Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2"%(self.imu.acceleration))
                    self.debug_print("Gyro X:%.2f, Y: %.2f, Z: %.2f radians/s"%(self.imu.gyro))
                    self.datalist.append(self.imu.acceleration)
                    self.datalist.append(self.imu.gyro)
                except Exception as e:
                    self.debug_print('[ERROR][IMU]',e)
                self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~') 
            elif self.position == "x+" or self.position == "x-" or self.position == "z+":
                pass
            else:
                self.debug_print('[Error]IMU Failure')
      
            #Test Motor Driver
            if ("DRV" in self.senlist) and (self.sensors.get('DRV') == True ):
                try:
                    self.debug_print('Motor Driver')
                    self.debug_print('[ACTIVE][Motor Driver]') #No function defined here yet to use the driver
                except Exception as e:
                    self.debug_print('[ERROR][Motor Driver]',e)
                self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~') 
            else:
                pass

            #Test Thermocouple
            if ("COUPLE" in self.senlist) and (self.sensors.get('COUPLE') == True ):
                try:
                    self.debug_print('Thermocouple')
                    self.debug_print(self.couple) #Unformatted
                    self.datalist.append(self.couple)
                except Exception as e:
                    self.debug_print('[ERROR][Thermocouple]',e)
                self.debug_print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~') 
            elif self.position == "z-":
                self.debug_print('[ERROR]Thermocouple Failure')
            else:
                pass

            self.debug_print('=======================================')
            time.sleep(rate) #Remove later for performance boost! 
        return self.datalist
    def __del__(self):
        self.debug_print("Object Destroyed!")

class AllFaces:
    def __init__(self,debug):
        
        self.debug = debug
        self.debug_print("Creating Face Objects...")
        self.BigFaceList=[]
        self.Face5 = Face(5,"y-",self.debug)
        self.Face4 = Face(4,"x+",self.debug)
        self.Face3 = Face(3,"x-",self.debug)
        self.Face2 = Face(2,"y+",self.debug)
        self.Face1 = Face(1,"z-",self.debug)
        self.Face0 = Face(0,"z+",self.debug)
        self.debug_print("Done!")


        #Initialize All Faces 
        try:
            self.Face0.Sensorinit(self.Face0.senlist,self.Face0.address)
        except Exception as e:
            self.debug_print('[ERROR][Face0 Initialization]' + str(e))

        try:
            self.Face1.Sensorinit(self.Face1.senlist,self.Face1.address)
        except Exception as e:
            self.debug_print('[ERROR][Face1 Initialization]' + str(e))
        
        try:
            self.Face2.Sensorinit(self.Face2.senlist,self.Face2.address)
        except Exception as e:
            self.debug_print('[ERROR][Face2 Initialization]' + str(e))

        try:
            self.Face3.Sensorinit(self.Face3.senlist,self.Face3.address)
        except Exception as e:
            self.debug_print('[ERROR][Face3 Initialization]' + str(e))
        
        try:
            self.Face4.Sensorinit(self.Face4.senlist,self.Face4.address)
        except Exception as e:
            self.debug_print('[ERROR][Face4 Initialization]' + str(e))
        
        try:
            self.Face5.Sensorinit(self.Face5.senlist,self.Face5.address)
        except Exception as e:
            self.debug_print('[ERROR][Face5 Initialization]' + str(e))
        
        self.debug_print("Faces Initialized")

    def debug_print(self,statement):
        if self.debug:
            print(co("[BIG_DATA]"+statement,"orange","bold")) 

    @property #driver sequence Getter 
    def sequence(self): 
        return self.Face1.drv,self.Face3.drv,self.Face4.drv

    @sequence.setter #setter
    def sequence(self, seq): 
        self.Face1.drv=seq
        self.Face3.drv=seq
        self.Face4.drv=seq

    def driver_actuate(self,duration):
        try:
            self.Face1.drv_actuate(duration)
            self.Face3.drv_actuate(duration)
            self.Face4.drv_actuate(duration)
        except Exception as e:
            print('Driver Test error: ' + str(e))

    def drvx_actuate(self,duration):
        try:
            self.Face4.drv_actuate(duration)
        except Exception as e:
            print('Driver Test error: ' + str(e))

    def drvy_actuate(self,duration):
        try:
            self.Face3.drv_actuate(duration)
        except Exception as e:
            print('Driver Test error: ' + str(e))

    def drvz_actuate(self,duration):
        try:
            self.Face1.drv_actuate(duration)
        except Exception as e:
            print('Driver Test error: ' + str(e))

    #Function that polls all of the sensors on all of the faces one time and prints the results. 
    def Face_Test_All(self):
        try:
            self.BigFaceList=[]
            self.debug_print("Creating Face List")
            self.BigFaceList.append(self.Face0.test_all(1,.1))
            self.BigFaceList.append(self.Face1.test_all(1,.1))
            self.BigFaceList.append(self.Face2.test_all(1,.1))
            self.BigFaceList.append(self.Face3.test_all(1,.1))
            self.BigFaceList.append(self.Face4.test_all(1,.1))
            self.BigFaceList.append(self.Face5.test_all(1,.1))

            for face in self.BigFaceList:
                self.debug_print(face)

        except Exception as e:
            self.debug_print('All Face test error:' + str(e))
        return self.BigFaceList
    
    def Get_IMU_Data(self):
        f1g=self.Face1.gyro#z-
        f4g=self.Face4.gyro#x+
        f5g=self.Face5.gyro#y-
        f1m=self.Face1.mag#z-
        f4m=self.Face4.mag#x+
        f5m=self.Face5.mag#y-
        return [f1g,f4g,f5g,f1m,f4m,f5m]
    
    def Get_Thermo_Data(self):
        f1t=self.Face1.couple[1]
        return f1t
        
    def __del__(self):
        del self.Face0
        del self.Face1
        del self.Face2
        del self.Face3
        del self.Face4
        del self.Face5
        self.debug_print("Object Destroyed!")





