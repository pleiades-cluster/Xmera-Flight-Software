"""
CircuitPython Version: 8.0.0 alpha

* Author(s): Nicole Maggard
"""
############################ TO DO: #################################
#Better Assign NVM registers
#Determine if NEOPIXEL in use
#Reinit metod
#Battery Voltage and current properties
#charging logical inquiry
#determine necessity of reset_vbus
#batteryData and PowerMode methods
#Burn Method
#use supervisor class to change code to execute on next run
#####################################################################

# Common CircuitPython Libs
import board, microcontroller
import busio, time, sys
from storage import mount,umount,VfsFat
from analogio import AnalogIn
import digitalio, sdcardio, pwmio

# Hardware Specific Libs
import rfm9x # Radio
import neopixel # RGB LED

# Common CircuitPython Libs
from os import listdir,stat,statvfs,mkdir,chdir,remove,rename
from bitflags import bitFlag,multiBitFlag,multiByte
from micropython import const
from debugcolor import co
import gc


# NVM register numbers
_BOOTCNT  = const(0)
_VBUSRST  = const(6)
_STATECNT = const(7)
_TOUTS    = const(9)
_GSRSP    = const(10)
_ICHRG    = const(11)
_FLAG     = const(16)

SEND_BUFF=bytearray(252)

class Satellite:
    # General NVM counters
    c_boot      = multiBitFlag(register=_BOOTCNT, lowest_bit=0,num_bits=8)
    c_vbusrst   = multiBitFlag(register=_VBUSRST, lowest_bit=0,num_bits=8)
    c_state_err = multiBitFlag(register=_STATECNT,lowest_bit=0,num_bits=8)
    c_gs_resp   = multiBitFlag(register=_GSRSP,   lowest_bit=0,num_bits=8)
    c_ichrg     = multiBitFlag(register=_ICHRG,   lowest_bit=0,num_bits=8)

    # Define NVM flags
    f_lowbatt  = bitFlag(register=_FLAG,bit=0)
    f_solar    = bitFlag(register=_FLAG,bit=1)
    f_burnarm  = bitFlag(register=_FLAG,bit=2)
    f_lowbtout = bitFlag(register=_FLAG,bit=3)
    f_gpsfix   = bitFlag(register=_FLAG,bit=4)
    f_shtdwn   = bitFlag(register=_FLAG,bit=5)

    def __init__(self):
        """
        Big init routine as the whole board is brought up.
        """
        self.BOOTTIME= const(time.time())
        self.NORMAL_TEMP=20
        self.NORMAL_BATT_TEMP=10
        self.NORMAL_MICRO_TEMP=20
        self.NORMAL_CHARGE_CURRENT=250
        self.NORMAL_BATTERY_VOLTAGE=7.5
        self.CRITICAL_BATTERY_VOLTAGE=7
        self.data_cache={}
        self.filenumbers={}
        self.image_packets=0
        self.urate = 115200
        self.vlowbatt=6.0
        self.send_buff = memoryview(SEND_BUFF)
        self.debug=True #Define verbose output here. True or False
        self.micro=microcontroller
        self.PowerMode="normal"
        self.hardware = {
                       'Radio1': False,
                       'SDcard': False,
                       'WDT':    False,
                       'Face0':  False,
                       'Face1':  False,
                       'Face2':  False,
                       'Face3':  False,
                       'Face4':  False,
                       'Face5':  False,
                       } 
        
        self.debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")

        self.debug_print("Initializing C&DH Hardware...")

        #Define Face Sensor Power MOSFETs
        self.xPosFet = digitalio.DigitalInOut(board.GP4)
        self.xPosFet.direction = digitalio.Direction.OUTPUT

        self.xNegFet = digitalio.DigitalInOut(board.GP5)
        self.xNegFet.direction = digitalio.Direction.OUTPUT

        self.yPosFet = digitalio.DigitalInOut(board.GP6)
        self.yPosFet.direction = digitalio.Direction.OUTPUT

        self.yNegFet = digitalio.DigitalInOut(board.GP7)
        self.yNegFet.direction = digitalio.Direction.OUTPUT

        self.zPosFet = digitalio.DigitalInOut(board.GP8)
        self.zPosFet.direction = digitalio.Direction.OUTPUT

        self.zNegFet = digitalio.DigitalInOut(board.GP13)
        self.zNegFet.direction = digitalio.Direction.OUTPUT

        self.all_faces_off()

        # Define SPI,I2C,UART | Note: i2c2 initialized in Big_Data
        try:
            self.i2c1  = busio.I2C(board.GP3,board.GP2,frequency = 400000)
        except Exception as e:
            self.debug_print("I2C Initialization error: " + str(e))
        try:
            self.spi = busio.SPI(board.GP10, board.GP11, board.GP12)
        except Exception as e:
            self.debug_print("SPI Initialization error: " + str(e))
        try:
            self.uart  = busio.UART(board.GP0,board.GP1,baudrate=self.urate)
        except Exception as e:
            self.debug_print("UART Initialization error: " + str(e))

        # Define filesystem stuff
        self.Errorlogfile="/sd/errors/log.txt"
        self.Facelogfile="/sd/data/FaceData.txt"
        self.Executepy="/sd/pytest/execute.py"

        # Define radio
        _rf_cs1 = digitalio.DigitalInOut(board.GP14)
        _rf_rst1 = digitalio.DigitalInOut(board.GP15)
        self.enable_rf = digitalio.DigitalInOut(board.GP16)
        self.radio1_DIO0=digitalio.DigitalInOut(board.GP17)
        
        # self.enable_rf.switch_to_output(value=False) # if U21
        self.enable_rf.switch_to_output(value=True) # if U7
        _rf_cs1.switch_to_output(value=True)
        _rf_rst1.switch_to_output(value=True)
        self.radio1_DIO0.switch_to_input()

        # Initialize SD card (always init SD before anything else on spi bus)
        try:
            # Baud rate depends on the card, 4MHz should be safe
            _sd = sdcardio.SDCard(self.spi, board.GP19, baudrate=4000000)
            _vfs = VfsFat(_sd)
            mount(_vfs, "/sd")
            self.fs=_vfs
            sys.path.append("/sd")
            self.hardware['SDcard'] = True
            try:
                try:
                    print("Checking path: " + self.logfile[:-4]+"00000.txt")
                    path=stat(self.logfile[:-4]+"00000.txt")
                except:
                    path=False
                try:
                    print("Checking path: " + self.Facelogfile[:-4]+"00000.txt")
                    path1=stat(self.Facelogfile[:-4]+"00000.txt")
                except:
                    path1=False
                if not path:
                    print("creating an Error log file")
                    self.new_file(self.logfile[3:-4])
                if not path1:
                    print("creating an Face log file")
                    self.new_file(self.Facelogfile[3:-4])
            except Exception as e:
                self.debug_print(f'Error creating one or more files {e}')

        except Exception as e:
            self.debug_print(f'[ERROR][SD Card]{e}')

        # Initialize Neopixel
        try:
            self.neopixel = neopixel.NeoPixel(board.GP18, 1, brightness=0.2, pixel_order=neopixel.GRB)
            self.neopixel[0] = (0,0,0)
            self.hardware['Neopixel'] = True
        except Exception as e:
            self.debug_print(f'[WARNING][Neopixel]{e}')

        # Initialize radio #1 - UHF
        # More of this is done in the Field class
        try:
            self.radio1 = rfm9x.RFM9x(self.spi, _rf_cs1, _rf_rst1,
                437.4,code_rate=8,baudrate=1320000)
            # Default LoRa Modulation Settings
            # Frequency: 437.4 MHz, SF7, BW125kHz, CR4/8, Preamble=8, CRC=True
            self.radio1.dio0=self.radio1_DIO0
            self.radio1.enable_crc=True
            self.radio1.ack_delay=0.2
            self.radio1.sleep()
            self.hardware['Radio1'] = True
        except Exception as e:
            self.debug_print(f'[ERROR][RADIO 1]{e}')
            
        self.debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")

        # Prints init state of C&DH hardware
        self.debug_print(str(self.hardware))

    # Method to reinitialize hardware
    def reinit(self):
        self.debug_print(str(self.hardware))

    @property
    def RGB(self):
        return self.neopixel[0]
    @RGB.setter
    def RGB(self,value):
        if self.hardware['Neopixel']:
            try:
                self.neopixel[0] = value
            except Exception as e:
                print(f'[WARNING]{e}')

    @property
    def burnarm(self):
        return self.f_burnarm
    @burnarm.setter
    def burnarm(self,value):
        self.f_burnarm=value

    @property
    def battery_voltage(self):
        vbat=0
        #Add code to inquire about battery voltage from EPS
        BatteryVoltage = (vbat/50)*(316+110)/110 # 316/110 voltage divider
        return BatteryVoltage # volts

    @property
    def charge_current(self):
        """
        LTC4121 solar charging IC with charge current monitoring
        See Programming the Charge Current section
        """
        charge = 0
        if self.solar_charging:
            #add code to inquire about charge current from EPS
            charge = ((charge*988)/3010)*1000
        return charge # mA

    @property
    def solar_charging(self):
        #add code to inquire if we are charging
        IsCharging=True
        return IsCharging

    #See if we need this or not
    '''@property
    def reset_vbus(self):
        # unmount SD card to avoid errors
        if self.hardware['SDcard']:
            try:
                umount('/sd')
                self.spi.deinit()
                time.sleep(3)
            except Exception as e:
                print('vbus reset error?', e)
                pass
        self._resetReg.drive_mode=digitalio.DriveMode.PUSH_PULL
        self._resetReg.value=1'''

    def log(self, msg):
        if self.hardware['SDcard']:
            with open(self.Errorlogfile, "a+") as f:
                t=int(time.monotonic())
                f.write('{}, {}\n'.format(t,msg))
    
    def create_pycode(self, msg):
        if self.hardware['SDcard']:
            try:
                with open(self.Executepy, 'w') as f:
                    if isinstance(msg,str):
                        f.write(msg)
                    else:
                        f.write('{}'.format(msg))
                f.close()
            except Exception as e:
                self.debug_print(f'Error making new code: {e}')

    def append_pycode(self, msg):
        if self.hardware['SDcard']:
            try:
                with open(self.Executepy, "a+") as f:
                    f.write('\n')
                    if isinstance(msg,str):
                        f.write(msg)
                    else:
                        f.write('{}'.format(msg))
                f.close()
            except Exception as e:
                self.debug_print(f'Error making new code: {e}')
    
    def update_pycode(self, msg):
        if self.hardware['SDcard']:
            try:
                with open("/sd/pytest/new_test.py", 'w') as f:
                    self.debug_print("about to overwrite data...")
                    if isinstance(msg,str):
                        f.write(msg)
                    else:
                        f.write('{}'.format(msg))
                f.close()
                remove(self.testpy)
                rename("/sd/pytest/new_test.py",self.testpy)
            except Exception as e:
                self.debug_print(f'Error making new code: {e}')

    def exec_pycode(self):
        if self.hardware['SDcard']:
            try:
                sys.path.append("/sd/pytest")
                import test
                sys.modules.pop('test')
            except Exception as e:
                self.debug_print(f"error importing: {e}")
    
    def Face_log(self, msg):
        if self.hardware['SDcard']:
            with open(self.Facelogfile, "a+") as f:
                t=int(time.monotonic())
                for face in msg:
                    f.write('{}, {}\n'.format(t,face))

    def print_file(self,filedir=None,binary=False):
        if filedir==None:
            return
        print('\n--- Printing File: {} ---'.format(filedir))
        if binary:
            with open(filedir, "rb") as file:
                print(file.read())
                print('')
        else:
            with open(filedir, "r") as file:
                for line in file:
                    print(line.strip())

    def timeout_handler(self):
        self.debug_print('Incrementing timeout register')
        if (self.micro.nvm[_TOUTS] + 1) >= 255:
            self.micro.nvm[_TOUTS]=0
            # soft reset
            self.micro.on_next_reset(self.micro.RunMode.NORMAL)
            self.micro.reset()
        else:
            self.micro.nvm[_TOUTS] += 1
        
    #Turns all of the Faces On (Defined before init because this fuction is called by the init)
    def all_faces_on(self):
        #Faces MUST init in this order or the uController will brown out. Cause unknown
        if self.hardware['Radio1']: self.radio1.sleep()
        time.sleep(2)
        self.xNegFet.value = False
        time.sleep(0.1)
        self.yPosFet.value = False
        time.sleep(0.1)
        self.yNegFet.value = False
        time.sleep(0.1)
        self.zPosFet.value = False
        time.sleep(0.1)
        self.zNegFet.value = False
        time.sleep(0.1)
        self.xPosFet.value = False
        time.sleep(1) #Sleep is to ideally stabilize the power 

    def all_faces_off(self):
        #De-Power Faces 
        self.xPosFet.value = True
        time.sleep(0.1)
        self.zNegFet.value = True
        time.sleep(0.1)
        self.zPosFet.value = True
        time.sleep(0.1)
        self.yNegFet.value = True
        time.sleep(0.1)
        self.yPosFet.value = True
        time.sleep(0.1)
        self.xNegFet.value = True
        time.sleep(1) #Sleep is to ideally stabilize the power 

    def debug_print(self,statement):
        if self.debug:
            print(co("[CDH]"+statement,"red","bold"))

    #Function is designed to interface with EPS board and obtain desired data
    def BatteryData(self):
        self.debug_print("Getting Battery Data...")
        #add more to logic to obtain data via uart

    #Function to ask EPS which mode we are in and how to manage hardware
    def PowerMode(self):
        self.debug_print("Seeing which power mode we are in...")
    

    def new_file(self,substring,binary=False):
        '''
        substring something like '/data/DATA_'
        directory is created on the SD!
        int padded with zeros will be appended to the last found file
        '''
        if self.hardware['SDcard']:
            ff=''
            n=0
            _folder=substring[:substring.rfind('/')+1]
            _file=substring[substring.rfind('/')+1:]
            print('Creating new file in directory: /sd{} with file prefix: {}'.format(_folder,_file))
            try: chdir('/sd'+_folder)
            except OSError:
                print('Directory {} not found. Creating...'.format(_folder))
                try: mkdir('/sd'+_folder)
                except Exception as e:
                    print(e)
                    return None
            for i in range(0xFFFF):
                ff='/sd{}{}{:05}.txt'.format(_folder,_file,(n+i)%0xFFFF)
                try:
                    if n is not None:
                        stat(ff)
                except:
                    n=(n+i)%0xFFFF
                    # print('file number is',n)
                    break
            print('creating file...',ff)
            if binary: b='ab'
            else: b='a'
            with open(ff,b) as f:
                f.tell()
            chdir('/')
            return ff

    def delete(self,substring):
        try:
            remove(substring)
        except Exception as e:
            print("failed to remove file: ", e)

    # Tell EPS how to burn wire
    def burn(self,burn_num,dutycycle=0,freq=1000,duration=1):
        self.debug_print("Executing Burn")

print("Creating C&DH object")
cdh = Satellite()
