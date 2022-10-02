"""
CircuitPython driver for PyCubed satellite board.
PyCubed Hardware Version: mainboard-v05
CircuitPython Version: 7.0.0 alpha
Library Repo: https://github.com/pycubed/library_pycubed.py

* Author(s): Max Holliday, Michael Pham, and Nicole Maggard
"""
########################### To-Do ##########################
#Return of the BMX160
############################################################


# Common CircuitPython Libs
import board, microcontroller
import busio, time, sys
from storage import mount,umount,VfsFat
from analogio import AnalogIn
import digitalio, sdcardio, pwmio

# Hardware Specific Libs
import pycubed_rfm9x # Radio
import neopixel # RGB LED
import bq25883 # USB Charger
import adm1176 # Power Monitor

# Common CircuitPython Libs
from os import listdir,stat,statvfs,mkdir,chdir,remove,rename
from bitflags import bitFlag,multiBitFlag,multiByte
from micropython import const
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
        print(gc.mem_free())
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
        self.hardware = {
                       'IMU':    False,
                       'Radio1': False,
                       'SDcard': False,
                       'WDT':    False,
                       'USB':    False,
                       'PWR':    False,
                       'Face0':  False,
                       'Face1':  False,
                       'Face2':  False,
                       'Face3':  False,
                       'Face4':  False,
                       'Face5':  False,
                       } 
        
        print(gc.mem_free())

        self.debug_print("Initializing PyCubed...")

        # Define burn wires:
        self._relayA = digitalio.DigitalInOut(board.RELAY_A)
        self._relayA.switch_to_output(drive_mode=digitalio.DriveMode.OPEN_DRAIN)
        self._resetReg = digitalio.DigitalInOut(board.VBUS_RST)
        self._resetReg.switch_to_output(drive_mode=digitalio.DriveMode.OPEN_DRAIN)

        # Define battery voltage
        self._vbatt = AnalogIn(board.BATTERY)

        # Define MPPT charge current measurement
        self._ichrg = AnalogIn(board.L1PROG)
        self._chrg = digitalio.DigitalInOut(board.CHRG)
        self._chrg.switch_to_input()

        # Define SPI,I2C,UART | Note: i2c2 initialized in Big_Data
        self.i2c1  = busio.I2C(board.SCL,board.SDA,frequency = 400000)
        self.spi   = board.SPI()
        self.uart  = busio.UART(board.TX,board.RX,baudrate=self.urate)

        # Define filesystem stuff
        self.logfile="/sd/errors/log.txt"
        self.Facelogfile="/sd/data/FaceData.txt"
        self.Imagelogfile="/sd/images/PIC.txt"
        self.testpy="/sd/pytest/test.py"

        # Define radio
        _rf_cs1 = digitalio.DigitalInOut(board.RF1_CS)
        _rf_rst1 = digitalio.DigitalInOut(board.RF1_RST)
        self.enable_rf = digitalio.DigitalInOut(board.EN_RF)
        self.radio1_DIO0=digitalio.DigitalInOut(board.RF1_IO0)
        
        # self.enable_rf.switch_to_output(value=False) # if U21
        self.enable_rf.switch_to_output(value=True) # if U7
        _rf_cs1.switch_to_output(value=True)
        _rf_rst1.switch_to_output(value=True)
        self.radio1_DIO0.switch_to_input()
        
        # Define Heater Pins 
        self.heater_en = self._relayA
        self.heater_en.direction = digitalio.Direction.OUTPUT
        self.heater_en.value = False
        
        self.heater_ctrl = digitalio.DigitalInOut(board.BURN1)
        self.heater_ctrl.direction = digitalio.Direction.OUTPUT
        self.heater_ctrl.value = False

        #Define Face Sensor Power MOSFETs
        self.xPosFet = digitalio.DigitalInOut(board.PB16)
        self.xPosFet.direction = digitalio.Direction.OUTPUT

        self.xNegFet = digitalio.DigitalInOut(board.PB22)
        self.xNegFet.direction = digitalio.Direction.OUTPUT

        self.yPosFet = digitalio.DigitalInOut(board.PA22)
        self.yPosFet.direction = digitalio.Direction.OUTPUT

        self.yNegFet = digitalio.DigitalInOut(board.PA19)
        self.yNegFet.direction = digitalio.Direction.OUTPUT

        self.zPosFet = digitalio.DigitalInOut(board.PB23)
        self.zPosFet.direction = digitalio.Direction.OUTPUT

        self.zNegFet = digitalio.DigitalInOut(board.PA20)
        self.zNegFet.direction = digitalio.Direction.OUTPUT
        #Make sure to verify that all of these definitions are as wired on the satellte

        #Spresense CS Definition:
        self.Spres_cold=digitalio.DigitalInOut(board.PB17)#this pin depends on the pycubed being used
        self.Spres_cold.direction=digitalio.Direction.OUTPUT
        self.Spresense_off()

        #List for image packets
        self.packetstring=[]

        # Initialize SD card (always init SD before anything else on spi bus)
        try:
            # Baud rate depends on the card, 4MHz should be safe
            _sd = sdcardio.SDCard(self.spi, board.SD_CS, baudrate=4000000)
            _vfs = VfsFat(_sd)
            mount(_vfs, "/sd")
            self.fs=_vfs
            sys.path.append("/sd")
            self.hardware['SDcard'] = True
            try:
                '''print(listdir("/sd/errors"))
                for i in range(0,1000):
                    h="00000"
                    if i >= 1000:
                        h="0"+str(i)
                    elif i >= 100:
                        h="00"+str(i)
                    elif i >= 10:
                        h="000"+str(i)
                    else:
                        h="0000"+str(i)
                    print("deleting path: " + self.logfile[11:]+h+".txt")
                    self.delete(self.logfile[11:]+h+".txt")'''
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
                try:
                    print("Checking path: " + self.Imagelogfile[:-4]+"00000.txt")
                    path2=stat(self.Imagelogfile[:-4]+"00000.txt")
                except:
                    path2=False
                if not path:
                    print("creating an Error log file")
                    self.new_file(self.logfile[3:-4])
                if not path1:
                    print("creating an Face log file")
                    self.new_file(self.Facelogfile[3:-4])
                if not path2:
                    print("creating an Image log file")
                    self.new_file(self.Imagelogfile[3:-4])
            except Exception as e:
                self.debug_print(f'[Error creating one or more files {e}')

        except Exception as e:
            self.debug_print(f'[ERROR][SD Card]{e}')

        # Initialize Neopixel
        try:
            self.neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, pixel_order=neopixel.GRB)
            self.neopixel[0] = (0,0,0)
            self.hardware['Neopixel'] = True
        except Exception as e:
            self.debug_print(f'[WARNING][Neopixel]{e}')

        # Initialize USB charger
        try:
            self.usb = bq25883.BQ25883(self.i2c1)
            self.usb.charging = False
            self.usb.wdt = False
            self.usb.led=False
            self.usb.charging_current=8 #400mA
            self.usb_charging=False
            self.hardware['USB'] = True
        except Exception as e:
            self.debug_print(f'[ERROR][USB Charger]{e}')

        # Initialize Power Monitor
        try:
            self.pwr = adm1176.ADM1176(self.i2c1)
            self.pwr.sense_resistor = 0.1
            self.hardware['PWR'] = True
        except Exception as e:
            self.debug_print(f'[ERROR][Power Monitor]{e}')

        # Initialize radio #1 - UHF
        try:
            self.radio1 = pycubed_rfm9x.RFM9x(self.spi, _rf_cs1, _rf_rst1,
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
            
        print(gc.mem_free())

        # Prints init state of PyCubed hardware
        print(self.hardware)

        # Initialize all of the Faces and their sensors
        self.debug_print("Powering On Faces")
        self.all_faces_on()

        # set PyCubed power mode
        self.power_mode = 'minimum'
        self.debug_print("Initialization Complete")

    def reinit(self,dev):
        dev=dev.lower()
        if dev=='pwr':
            try:
                self.pwr = adm1176.__init__(self.i2c1)
            except Exception as e:
                self.debug_print(e)
                
        elif dev=='usb':
            self.usb.__init__(self.i2c1)
        elif dev=='imu':
            self.IMU.__init__(self.i2c1)
        else:
            print('Invalid Device? ->',dev)


    '''
    Code to toggle on / off individual faces
    '''

    '''
    @property
    def Face0_state(self):
        return self.hardware['Face0']

    @Face0_state.setter
    def Face0_state(self,value):
        if value:
            try:
                self.zPosFet.value = False
                self.hardware['Face0'] = True
                self.debug_print("z Face Powered On")
            except Exception as e:
                self.debug_print('[WARNING][Face0]',e)
                self.hardware['Face0'] = False
        else:
            self.zPosFet.value = True
            self.hardware['Face0'] = False
            self.debug_print("z+ Face Powered Off")
    
    '''
    

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
    def charge_batteries(self):
        if self.hardware['USB']:
            return self.usb_charging
    @charge_batteries.setter
    def charge_batteries(self,value):
        if self.hardware['USB']:
            self.usb_charging=value
            self.usb.led=value
            self.usb.charging=value

    @property
    def battery_voltage(self):
        _vbat=0
        for _ in range(50):
            _vbat+=self._vbatt.value * 3.3 / 65536
        _voltage = (_vbat/50)*(316+110)/110 # 316/110 voltage divider
        return _voltage # volts

    @property
    def system_voltage(self):
        if self.hardware['PWR']:
            try:
                return self.pwr.read()[0] # volts
            except Exception as e:
                print(f'[WARNING][PWR Monitor]{e}')
        else:
            print('[WARNING] Power monitor initialization issue')


    @property
    def current_draw(self):
        """
        current draw from batteries
        NOT accurate if powered via USB
        """
        if self.hardware['PWR']:
            idraw=0
            try:
                for _ in range(50): # average 50 readings
                    idraw+=self.pwr.read()[1]
                return (idraw/50)*1000 # mA
            except Exception as e:
                print(f'[WARNING][PWR Monitor]{e}')
        else:
            print('[WARNING] Power monitor initialization issue')

    @property
    def charge_current(self):
        """
        LTC4121 solar charging IC with charge current monitoring
        See Programming the Charge Current section
        """
        _charge = 0
        if self.solar_charging:
            _charge = self._ichrg.value * 3.3 / 65536
            _charge = ((_charge*988)/3010)*1000
        return _charge # mA

    @property
    def solar_charging(self):
        return not self._chrg.value

    @property
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
        self._resetReg.value=1

    def log(self, msg):
        if self.hardware['SDcard']:
            with open(self.logfile, "a+") as f:
                t=int(time.monotonic())
                f.write('{}, {}\n'.format(t,msg))
    
    def create_pycode(self, msg):
        if self.hardware['SDcard']:
            try:
                with open(self.testpy, 'w') as f:
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
                with open(self.testpy, "a+") as f:
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
                    
    def Image_log(self, msg):
        if self.hardware['SDcard']:
            with open(self.Imagelogfile, "a+") as f:
                f.write(*msg, sep='')

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
        print('Incrementing timeout register')
        if (self.micro.nvm[_TOUTS] + 1) >= 255:
            self.micro.nvm[_TOUTS]=0
            # soft reset
            self.micro.on_next_reset(self.micro.RunMode.NORMAL)
            self.micro.reset()
        else:
            self.micro.nvm[_TOUTS] += 1
            
    #Function to turn on the battery heater
    def heater_on(self):
        self.heater_en.value = True
        self.heater_ctrl.value = True
    
    #Function to turn off the batter heater
    def heater_off(self):
        self.heater_en.value = False
        self.heater_ctrl.value = False

    #Function to wake spresense
    def Spresense_on(self):
        self.Spres_cold.value=False

    #Function to send spresense to sleep
    def Spresense_off(self):
        self.Spres_cold.value=True
        
    #Turns all of the Faces On (Defined before init because this fuction is called by the init)
    def all_faces_on(self):
        #Faces MUST init in this order or the uController will brown out. Cause unknown
        self.radio1.sleep()
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
        print(statement)

    #Function is designed to read battery data and take some action to maintain

    def battery_manager(self):
        self.debug_print(f'Battery Manager Started')

        vbatt=self.battery_voltage
        ichrg=self.charge_current
        idraw=self.current_draw
        vsys=self.system_voltage
        micro_temp=self.micro.cpu.temperature
        batt_temp= 30  #TESTTEST TEST TEST Positon 1 is the tip temperature

        pwr_list = [vbatt, ichrg, idraw, vsys]

        if any(elem is None for elem in pwr_list):
            self.debug_print('Reinitializing Power Monitor')
            self.reinit('pwr')

        
        self.debug_print(f'BATTERY Temp: {batt_temp} C')
        self.debug_print(f'MICROCONTROLLER Temp: {micro_temp} C')

        try:
            if batt_temp < self.NORMAL_BATT_TEMP:
                #turn on heat pad
                self.debug_print("Turning heatpad on")
            elif batt_temp > self.NORMAL_TEMP :
                #make sure heat pad is lowered?
                if batt_temp > self.NORMAL_TEMP + 20 :
                    #turn heat pad off
                    self.debug_print(f'Initiating Battery Protection Protocol due to overheatting')

            self.debug_print(f"charge current: {ichrg} mA, and battery voltage: {vbatt} V")
            self.debug_print(f"draw current: {idraw} mA, and system voltage: {vsys} V")
            
            try:
                if idraw>ichrg:
                    self.debug_print("Beware! The Satellite is drawing more power than receiving")
            except:
                pass

            if vbatt < self.CRITICAL_BATTERY_VOLTAGE:
                self.powermode('crit')
                self.debug_print(f'[CRITICAL POWER] Attempting to shutdown unnecessary systems')

            elif ichrg < self.NORMAL_CHARGE_CURRENT and vbatt < self.NORMAL_BATTERY_VOLTAGE:
                self.powermode('min')
                self.debug_print(f'[MINIMUM POWER] Attempting to shutdown unnecessary systems')
                
            elif vbatt > self.NORMAL_BATTERY_VOLTAGE+.5:
                self.powermode('max')
                self.debug_print(f'[MAXIMUM POWER] Attempting to turn on all systems')
                
            elif vbatt < self.NORMAL_BATTERY_VOLTAGE+.3 and self.power_mode=='maximum':
                self.powermode('norm')
                self.debug_print(f'[NORMAL POWER] Attempting to turn off high power systems')
        
        except Exception as e:
            print(e)

    def powermode(self,mode):
        """
        Configure the hardware for minimum or normal power consumption
        Add custom modes for mission-specific control
        """
        try: 

            if 'crit' in mode:
                self.RGB = (0,0,0)
                self.neopixel.brightness=0
                self.Spresense_off()
                self.enable_rf.value = False
                if self.hardware['PWR']:
                    self.pwr.config('V_CONT,I_CONT')
                self.all_faces_off()
                
                self.power_mode = 'critical'

            elif 'min' in mode:
                self.RGB = (0,0,0)
                self.neopixel.brightness=0
                self.enable_rf.value = True
                self.Spresense_off()
                if self.hardware['PWR']:
                    self.pwr.config('V_CONT,I_CONT')
                self.all_faces_off()

                self.power_mode = 'minimum'

            elif 'norm' in mode:
                self.enable_rf.value = True
                if self.hardware['PWR']:
                    self.pwr.config('V_CONT,I_CONT')
                self.power_mode = 'normal'
                self.Spresense_off()
                # don't forget to reconfigure radios, gps, etc...

            elif 'max' in mode:
                self.enable_rf.value = True
                if self.hardware['PWR']:
                    self.pwr.config('V_CONT,I_CONT')
                self.power_mode = 'maximum'
        
        except Exception as e: 
            self.debug_print(e)
            pass
    

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

    def burn(self,burn_num,dutycycle=0,freq=1000,duration=1):
        """
        Operate burn wire circuits. Wont do anything unless the a nichrome burn wire
        has been installed.

        IMPORTANT: See "Burn Wire Info & Usage" of https://pycubed.org/resources
        before attempting to use this function!

        burn_num:  (string) which burn wire circuit to operate, must be either '1' or '2'
        dutycycle: (float) duty cycle percent, must be 0.0 to 100
        freq:      (float) frequency in Hz of the PWM pulse, default is 1000 Hz
        duration:  (float) duration in seconds the burn wire should be on
        """
        # convert duty cycle % into 16-bit fractional up time
        dtycycl=int((dutycycle/100)*(0xFFFF))
        print('----- BURN WIRE CONFIGURATION -----')
        print('\tFrequency of: {}Hz\n\tDuty cycle of: {}% (int:{})\n\tDuration of {}sec'.format(freq,(100*dtycycl/0xFFFF),dtycycl,duration))
        # create our PWM object for the respective pin
        # not active since duty_cycle is set to 0 (for now)
        if '1' in burn_num:
            burnwire = pwmio.PWMOut(board.BURN1, frequency=freq, duty_cycle=0)
        elif '2' in burn_num:
            burnwire = pwmio.PWMOut(board.BURN2, frequency=freq, duty_cycle=0)
        else:
            return False
        # Configure the relay control pin & open relay
        self._relayA.drive_mode=digitalio.DriveMode.PUSH_PULL
        self._relayA.value = 1
        self.RGB=(255,0,0)
        # Pause to ensure relay is open
        time.sleep(0.5)
        # Set the duty cycle over 0%
        # This starts the burn!
        burnwire.duty_cycle=dtycycl
        time.sleep(duration)
        # Clean up
        self._relayA.value = 0
        burnwire.duty_cycle=0
        self.RGB=(0,0,0)
        burnwire.deinit()
        self._relayA.drive_mode=digitalio.DriveMode.OPEN_DRAIN
        return True

print("Initializing CubeSat")
cubesat = Satellite()
