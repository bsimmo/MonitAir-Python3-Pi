''' RPi
PM2/5/10 SDS021 on USB, GPS ublox mt-8030 on UART (mini), T/P/H/V BME680 on i2c, DS180B20 on 1-wire gpio
Ben Simmons
'''

##### Libraries #####
import serial   #to read from  serial UART
import json #for bme & MQTT
import subprocess #for bme
from statistics import median #for bme
from datetime import datetime
from time import sleep

import pynmea2  #NMEA GPS splitter sudo pip3 install pynmea2
from w1thermsensor import W1ThermSensor #sudo pip3 install w1thermsensor or sudo apt install w1thermsensor
from pysds011 import SDS011 #



##### Logging Settings #####
FILENAME="monitAirLog"
WRITE_FREQUENCY = 30
    # gps
TIMESTAMP = True
LATITUDE = True
LONGITUDE = True
ALTITUDE = True
    # ground temp
W1THERM = True
    # pm2.5 & pm10
SDS = True
    # IAQ , Temp/Pressre/Humidity
BME_IAQ=False
BME_TPH=False


##### Functions #####
def file_setup(filename):
    header =[]
    if W1THERM:
        header.append("gndTemp")
    if SDS:
        header.extend(["pm25","pm10"])
    if BME_IAQ:
        header.extend(["iaq","iaq_qual"])
    if BME_TPH:        
        header.extend(["bme_temp","pressure","humidity"])        
    if TIMESTAMP:
        header.append("time")
    if LATITUDE:
        header.extend(["latitude","latdir"])
    if LONGITUDE:
        header.extend(["longitude","longdir"])
    if ALTITUDE:
        header.append("altitude")


        
        
    header.append("DateTime")

    with open(filename,"w") as f:
        f.write(",".join(str(value) for value in header)+ "\n")



def log_data(sensor_data):
    output_string = ",".join(str(value) for value in sensor_data)
    batch_data.append(output_string)


def bme680_go():
    for line in iter(proc.stdout.readline, ''):
        lineJSON = json.loads(line.decode("utf-8")) # process line-by-line
        lineDict = dict(lineJSON)

        listIAQ_Accuracy.append(int(lineDict['IAQ_Accuracy']))
        listPressure.append(float(lineDict['Pressure']))
        #listGas.append(int(lineDict['Gas']))
        listTemperature.append(float(lineDict['Temperature']))
        listIAQ.append(float(lineDict['IAQ']))
        listHumidity.append(float(lineDict['Humidity']))
        #listStatus.append(int(lineDict['Status']))

        if len(listIAQ_Accuracy) == 20:
            #generate the median for each value
            IAQ_Accuracy = median(listIAQ_Accuracy)
            Pressure = int(median(listPressure))
            #Gas = median(listGas)
            Temperature = round(median(listTemperature),1)
            IAQ = int(median(listIAQ))
            Humidity = int(median(listHumidity))
            #Status = median(listStatus)

            #clear lists
            listIAQ_Accuracy.clear()
            listPressure.clear()
            #listTemperature.clear()
            listIAQ.clear()
            listHumidity.clear()
            #listStatus.clear()
    return IAQ, IAQ_Accuracy, Temperature, Pressure, Humidity
        

def get_sensor_data(msg):
    sensor_data=[]
    if BME_IAQ or BME_TPH:
        bme_values=bme680_go()
    if W1THERM:
        sensor_data.append(round(w1sensor.get_temperature(),1)) #this adds an ~750ms delay
    if SDS:
        sds_values = sds_sensor.query()
        sensor_data.extend([round(sds_values[0],0),round(sds_values[1],0)])
    if BME_IAQ:
        sensor_data.extend([bme_values[0],bme_values[1]])
    if BME_TPH:
        sensor_data.extend([bme_values[2],bme_values[3],bme_values[4]])        
    if TIMESTAMP:
        sensor_data.append(msg.timestamp)
    if LATITUDE:
        sensor_data.extend([msg.latitude,msg.lat_dir])
    if LONGITUDE:
        sensor_data.extend([msg.longitude,msg.lon_dir])
    if ALTITUDE:
        sensor_data.append(msg.altitude)
    if NUMSATS:
        sensor_data.append(msg.num_sats)

    sensor_data.append(datetime.now())
    return sensor_data


##### Main Program #####
serialPort = serial.Serial("/dev/serial0", 9600, timeout=0.5) #opens serial port, may need to change ttyAMA0 to whatever is now used e.g. serial0
batch_data= []

if W1THERM:
    w1sensor = W1ThermSensor()

if SDS:
    sds_sensor = SDS011('/dev/ttyUSB0')
    
if BME_IAQ or BME_TPH:
    print("BME680 Start")
    proc = subprocess.Popen(['./bsec_bme680'], stdout=subprocess.PIPE)
    listIAQ_Accuracy = []
    listPressure = []
    #listGas = []
    listTemperature = []
    listIAQ = []
    listHumidity  = []
    #listStatus = []

    #set filename based on generic or given filename and current date-time
if FILENAME == "":
    filename = "Log-"+str(datetime.now())+".csv"
else:
    filename = FILENAME+"-"+str(datetime.now())+".csv"

    #setup file and add headers
file_setup(filename)

while True:
    strip = serialPort.readline()
    if strip.find(b'GGA') > 0:
        msg = pynmea2.parse(strip.decode('utf-8'))
        sensor_data = get_sensor_data(msg)
        print(sensor_data)
        log_data(sensor_data)

        if len(batch_data) >= WRITE_FREQUENCY:
            print("Writing monitAir Data to file..")
            with open(filename,"a") as f:
                for line in batch_data:
                    f.write(line + "\n")
                batch_data = []
