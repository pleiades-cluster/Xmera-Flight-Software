'''
Created by Nicole Maggard and Michael Pham 8/19/2022
This is where the processes get scheduled, and satellite operations are handeled
''' 
from CDH import cdh as c
import asyncio
from debugcolor import co
import time
import gc #Garbage collection

debug=True

def debug_print(statement):
        if debug:
            print(co("[MAIN]"+statement,"blue","bold"))

debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")

import functions
f=functions.functions(c)
debug_print("Remaining memory: " + str(gc.mem_free()) + " Bytes")
#setup global vars below:

#setup all hardware below:
c.neopixel.auto_write=False
#test the battery:
c.BatteryData()
#sleep for some time
time.sleep(10) #Set to 120 for flight
debug_print("Burn status: " + str(c.burnarm))

if not c.burnarm :
    c.burn("2",0.5,4000,3)
    c.burnarm=True
    time.sleep(3)
else:
    pass

c.BatteryData()

def critical_power_operations():
    f.beacon()
    f.listen()
    f.state_of_health()  
     
    f.Long_Hybernate()

def minimum_power_operations():
    
    f.beacon()
    f.listen()
    f.state_of_health()   
    
    f.Short_Hybernate() 
        
def normal_power_operations():
    
    debug_print("Entering Norm Operations")
    FaceData=[]
    #Defining L1 Tasks
    def check_power():
        
        c.BatteryData()
        
        if c.PowerMode == 'normal' or c.PowerMode == 'maximum': 
            pwr = True
        else:
            pwr = False

        debug_print(c.PowerMode)
        return pwr
    
    async def s_lora_beacon():
        
        while check_power():
            f.beacon()
            f.listen()
            f.state_of_health()   
            time.sleep(1) # Guard Time
            
            await asyncio.sleep(30)

    async def g_face_data():
        
        while check_power():

            FaceData=[]

            try:
                debug_print("Getting face data...")
                FaceData = f.all_face_data()

                debug_print(str(FaceData))
                
            except Exception as e:
                debug_print(f'Error acquiring face data: {e}')
            
            gc.collect()
            
            await asyncio.sleep(60)
    
    async def l_face_data():
        
        await asyncio.sleep(15)
        
        while check_power():
            try:
                debug_print("Looking to log face data...")

                try:
                    debug_print("Logging face data...")
                    c.Face_log(FaceData)
                    
                except asyncio.TimeoutError as t:
                    debug_print(f'Outta time! {t}')

            except asyncio.TimeoutError as t:
                debug_print(f'Outta time! {t}')
            
            gc.collect()
            
            await asyncio.sleep(45)
    
    async def s_face_data():

        await asyncio.sleep(20)

        while check_power():
            try:
                debug_print("Looking to send face data...")
                f.send_face()
                
            except asyncio.TimeoutError as t:
                debug_print(f'Outta time! {t}')
            
            gc.collect()
            
            await asyncio.sleep(200)

    async def s_imu_data():

        await asyncio.sleep(45)
        
        while check_power():
            
            try:
                debug_print("Looking to get imu data...")
                IMUData=[]

                debug_print("IMU has baton")
                IMUData = f.get_imu_data()
                f.send(IMUData)
                f.face_data_baton = False

            except Exception as t:
                debug_print(f'Outta time! {t}')
                
            gc.collect()
            
            await asyncio.sleep(100)
    
    async def main_loop():
        #log_face_data_task = asyncio.create_task(l_face_data())
            
        t1 = asyncio.create_task(s_lora_beacon())
        t2 = asyncio.create_task(s_face_data())
        t3 = asyncio.create_task(l_face_data())
        t4 = asyncio.create_task(s_imu_data())
        t5 = asyncio.create_task(g_face_data())
        
        await asyncio.gather(t1,t2,t3,t4,t5)
        
    asyncio.run(main_loop())

def max_power_operations():
    #do L2 tasks
    try:
        f.Detumble()
    except Exception as e:
        debug_print("Error Detumbling: " + str(e))

######################### MAIN LOOP ##############################
while True:
    #L0 automatic tasks no matter the battery level
    c.BatteryData()
    
    if c.PowerMode == 'critical':
        critical_power_operations()
        
    elif c.PowerMode == 'minimum':
        minimum_power_operations()
        
    elif c.PowerMode == 'normal':
        normal_power_operations()
        
    elif c.PowerMode == 'maximum':
        max_power_operations()
        normal_power_operations()
        
    else:
        f.listen()
