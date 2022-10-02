'''
Created by Nicole Maggard and Michael Pham 8/19/2022
This is where the processes get scheduled, and satellite operations are handeled
''' 
from pycubed import cubesat as c
import asyncio
import time
import gc #Garbage collection

print(gc.mem_free())

import functions
f=functions.functions(c)
print(gc.mem_free())
#setup global vars below:
lora_beacon = "KN6NAQ Hello I am Yearling! IHBPFJASTMNE! KN6NAQ"

#setup all hardware below:
c.neopixel.auto_write=False
#test the battery:
c.battery_manager()
#sleep for some time
time.sleep(10) #Set to 120 for flight
print("Burn status: ", c.burnarm)

if not c.burnarm :
    c.burn("2",0.5,4000,3)
    c.burnarm=True
    time.sleep(3)
else:
    pass

c.battery_manager()
f.battery_heater()
c.battery_manager()

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
    
    print("Entering Norm Operations")
    FaceData=[]
    #Defining L1 Tasks
    def check_power():
        
        c.battery_manager()
        f.battery_heater()
        c.battery_manager() #Second check to make sure we have enough power to continue
        
        if c.power_mode == 'normal' or c.power_mode == 'maximum': 
            pwr = True
        else:
            pwr = False

        if c.debug: print(c.power_mode)
        return pwr
    
    async def s_lora_beacon():
        
        while check_power():
            f.beacon()
            f.listen()
            f.state_of_health()   
            time.sleep(1) # Guard Time
            
            await asyncio.sleep(30)

    async def s_picture():
        
        while check_power():
            if f.hasImage:
                try:
                    f.log_image_data(ImageData)
                except Exception as e:
                    print("error logging image data. ",e)
                try:
                    f.send_image()
                except Exception as e:
                    print("error sending image data. ",e)
            time.sleep(1) # Guard Time
            
            await asyncio.sleep(120)

    async def g_picture():
        
        while check_power():
            try:
                if c.power_mode == "maximum" and not f.hasImage:
                    ImageData=f.get_picture()
                    if f.image_packets < 40:
                        time.sleep(1)
                    else:
                        f.hasImage=True
            except Exception as e:
                print("error getting image data. ",e)
            time.sleep(1) # Guard Time
            
            await asyncio.sleep(240)

    async def g_face_data():
        
        while check_power():

            FaceData=[]

            try:
                print("Getting face data...")
                FaceData = f.all_face_data()

                print(FaceData)
                
            except Exception as t:
                print(f'Outta time! {t}')
            
            gc.collect()
            
            await asyncio.sleep(60)
    
    async def l_face_data():
        
        await asyncio.sleep(15)
        
        while check_power():
            try:
                print("Looking to log face data...")

                try:
                    print("Logging face data...")
                    c.Face_log(FaceData)
                    
                except asyncio.TimeoutError as t:
                    print(f'Outta time! {t}')

            except asyncio.TimeoutError as t:
                print(f'Outta time! {t}')
            
            gc.collect()
            
            await asyncio.sleep(45)
    
    async def s_face_data():

        await asyncio.sleep(20)

        while check_power():
            try:
                print("Looking to send face data...")
                f.send_face()
                
            except asyncio.TimeoutError as t:
                print(f'Outta time! {t}')
            
            gc.collect()
            
            await asyncio.sleep(200)

    async def s_imu_data():

        await asyncio.sleep(45)
        
        while check_power():
            
            try:
                print("Looking to get imu data...")
                IMUData=[]

                print("IMU has baton")
                IMUData = f.get_imu_data()
                f.send(IMUData)
                f.face_data_baton = False

            except Exception as t:
                print(f'Outta time! {t}')
                
            gc.collect()
            
            await asyncio.sleep(100)
    
    async def main_loop():
        #log_face_data_task = asyncio.create_task(l_face_data())
            
        t1 = asyncio.create_task(s_lora_beacon())
        t2 = asyncio.create_task(s_face_data())
        t3 = asyncio.create_task(l_face_data())
        t4 = asyncio.create_task(s_imu_data())
        t5 = asyncio.create_task(g_face_data())
        t6 = asyncio.create_task(g_picture())
        t7 = asyncio.create_task(s_picture())
        
        await asyncio.gather(t1,t2,t3,t4,t5,t6,t7)
        
    asyncio.run(main_loop())

    #f.torque(IMUData)
    
    #ErrorData=f.get_error_data()
    #f.log_error_data(ErrorData)

def max_power_operations():
    #do L2 tasks
    #only use images > 4KB for usefulness
    attempt=0
    try:
        while attempt < 2 and not f.hasImage:
            attempt+=1
            ImageData=f.get_picture()
            if f.image_packets < 40:
                c.battery_manager()
                time.sleep(1)
            else:
                f.hasImage=True
            if c.power_mode == 'normal':
                break
        if f.hasImage:
            try:
                f.log_image_data(ImageData)
            except Exception as e:
                print("error logging image data. ",e)
            f.send_image()
    except Exception as e:
        print("Error getting image: ",e)

######################### MAIN LOOP ##############################
while True:
    #L0 automatic tasks no matter the battery level
    c.battery_manager()
    
    if c.power_mode == 'critical':
        critical_power_operations()
        
    elif c.power_mode == 'minimum':
        minimum_power_operations()
        
    elif c.power_mode == 'normal':
        normal_power_operations()
        
    elif c.power_mode == 'maximum':
        max_power_operations()
        normal_power_operations()
        
    else:
        f.listen()
