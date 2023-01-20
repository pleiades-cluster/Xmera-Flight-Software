"""
CircuitPython Version: 8.0.0 alpha

* Author(s): Nicole Maggard
"""
############################ TO DO: #################################
#Make sure EPS board gets updated for the LTC4121 and then refer to pycubed.py for init
#Work on Battery Manager and Burn methods
#Assign VBUS_RESET, EN_BURN1, EN_BURN2, BURNRELAY1, BURNRELAY2, and UARTGPIO5 pins
#Better Assign NVM registers
#Determine if NEOPIXEL in use
#Battery Voltage and current properties
#charging logical inquiry
#determine necessity of reset_vbus
#batteryData and PowerMode methods
#Burn Method
#use supervisor class to change code to execute on next run
#####################################################################

# Common CircuitPython Libs
import board, microcontroller
import busio, time
import digitalio, pwmio

# Hardware Specific Libs
import neopixel # RGB LED
import adm1176
import bq28400

# Common CircuitPython Libs
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
                       'Neopixel':  False,
                       'I2C1':      False,
                       'I2C2':      False,
                       'SPI':       False,
                       'UART':      False,
                       'PWR MON':   False,
                       'BAT PROT':  False,
                       } 
        
        self.debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")

        self.debug_print("Initializing EPS Hardware...")

        # Define SPI,I2C,UART | Note: i2c2 initialized in Big_Data
        try:
            self.i2c1  = busio.I2C(board.GP9,board.GP8,frequency = 400000)
            self.hardware['I2C1'] = True
        except Exception as e:
            self.debug_print("I2C1 Initialization error: " + str(e))
        try:
            self.i2c2  = busio.I2C(board.GP7,board.GP6,frequency = 400000)
            self.hardware['I2C2'] = True
        except Exception as e:
            self.debug_print("I2C2 Initialization error: " + str(e))
        try:
            self.spi = busio.SPI(board.GP2, board.GP3, board.GP4)
            self.hardware['SPI'] = True
        except Exception as e:
            self.debug_print("SPI Initialization error: " + str(e))
        try:
            self.uart  = busio.UART(board.GP0,board.GP1,baudrate=self.urate)
            self.hardware['UART'] = True
        except Exception as e:
            self.debug_print("UART Initialization error: " + str(e))
            self.debug_print("Will attempt to reinitialize. If later unsuccessful, C&DH should check shared memory")

        # Initialize Power Monitor
        try:
            self.pwr = adm1176.ADM1176(self.i2c1)
            self.pwr.sense_resistor = 0.1
            self.hardware['PWR MON'] = True
        except Exception as e:
            self.debug_print("Power Monitor Initialization error: " + str(e))

        # Initialize Battery Protection IC
        try:
            self.bpi = bq28400.BQ28400(self.i2c2)
            self.bpi.charging = False
            self.bpi.wdt = False
            self.bpi.led=False
            self.bpi.charging_current=8 #400mA
            self.hardware['BAT PROT'] = True
        except Exception as e:
            self.debug_print(f'[ERROR][USB Charger]{e}')

        # Initialize Neopixel
        try:
            self.neopixel = neopixel.NeoPixel(board.GP18, 1, brightness=0.2, pixel_order=neopixel.GRB)
            self.neopixel[0] = (0,0,0)
            self.hardware['Neopixel'] = True
            
        except Exception as e:
            self.debug_print("Neopixel Initialization error: " + str(e))
            
        self.debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")

        # Prints init state of EPS hardware
        self.debug_print(str(self.hardware))

    # Method to reinitialize hardware
    def reinit(self):
        self.debug_print("Reinitializing EPS Hardware...")

        # Define SPI,I2C,UART | Note: i2c2 initialized in Big_Data
        try:
            if not self.hardware['I2C']:
                self.i2c1  = busio.I2C(board.GP3,board.GP2,frequency = 400000)
                self.hardware['I2C'] = True
        except Exception as e:
            self.debug_print("I2C Initialization error: " + str(e))
        try:
            if not self.hardware['SPI']:
                self.spi = busio.SPI(board.GP10, board.GP11, board.GP12)
                self.hardware['SPI'] = True
        except Exception as e:
            self.debug_print("SPI Initialization error: " + str(e))
        try:
            if not self.hardware['UART']:
                self.uart  = busio.UART(board.GP0,board.GP1,baudrate=self.urate)
                self.hardware['UART'] = True
        except Exception as e:
            self.debug_print("UART Initialization error: " + str(e))
            self.debug_print("Will attempt to reinitialize. If later unsuccessful, C&DH should check shared memory")

        # Initialize Power Monitor
        try:
            if not self.hardware['PWR MON']:
                self.pwr = adm1176.ADM1176(self.i2c1)
                self.pwr.sense_resistor = 0.1
                self.hardware['PWR MON'] = True
        except Exception as e:
            self.debug_print("Power Monitor Initialization error: " + str(e))

        # Initialize Neopixel
        try:
            if not self.hardware['NeoPixel']:
                self.neopixel = neopixel.NeoPixel(board.GP18, 1, brightness=0.2, pixel_order=neopixel.GRB)
                self.neopixel[0] = (0,0,0)
                self.hardware['Neopixel'] = True
            
        except Exception as e:
            self.debug_print("Neopixel Initialization error: " + str(e))
            
        self.debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")
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
                self.debug_print("Error setting Neopixel value: " + str(e))

    @property
    def burnarm(self):
        return self.f_burnarm

    @burnarm.setter
    def burnarm(self,value):
        self.f_burnarm=value

    @property
    def battery_voltage(self):
        vbat=0
        #Add code to inquire about battery voltage from battery protection IC
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

    def timeout_handler(self):
        self.debug_print('Incrementing timeout register')
        if (self.micro.nvm[_TOUTS] + 1) >= 255:
            self.micro.nvm[_TOUTS]=0
            # soft reset
            self.micro.on_next_reset(self.micro.RunMode.NORMAL)
            self.micro.reset()
        else:
            self.micro.nvm[_TOUTS] += 1

    def debug_print(self,statement):
        if self.debug:
            print(co("[EPS]"+statement,"red","bold"))

    #Function is designed to interface with C&DH board and obtain desired data
    def BatteryData(self):
        self.debug_print("Sending Battery Data...")
        #add more to logic to send data via uart

    #Function to determine powerstate based on battery characteristics
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

    # Function to burn the wire tying the antennas down
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

print("Creating EPS object")
eps = Satellite()
