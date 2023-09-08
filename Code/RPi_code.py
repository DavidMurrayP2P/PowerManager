#!/usr/bin/python3

import RPi.GPIO as GPIO
import os
import datetime
import sys
import time
import subprocess
from twython import Twython

# Configure the GPIO pins for data transfer
ALIVE_PIN1 = 16
ALIVE_PIN2 = 20

START_PIN = 13
CLOCK_PIN = 19
DATA_PIN = 26

shutdown_start_hour = 23
shutdown_end_hour = 6

GPIO.setwarnings(False)

from twitter_auth import (
    consumer_key,
    consumer_secret,
    access_token,
    access_token_secret
)

twitter = Twython(
    consumer_key,
    consumer_secret,
    access_token,
    access_token_secret
)

def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        uptime_hours = (uptime_seconds/3600)
    uptime_hours = str(round(uptime_hours, 2))
    return uptime_hours

def get_temp():
    temp = os.popen('vcgencmd measure_temp').readline()
    temp= temp.replace("temp=","").replace("'C\n","")
    print("The Pi Temp: " + str(temp) + " C")
    return temp

def tweet_message(event):
    message = (str(dev_id) + " " + str(event) + "\n" + "Uptime: " + str(uptime) + " hours\n" + "Batt: " + str(battery_voltage) + "V \n" + "Temp: " + str(temp) + " degrees")
    print(message)

    #print ("Taking photo")
    #os.system('libcamera-still -o /home/pi/camera/cam.jpg')
    #image = open("/home/pi/camera/cam.jpg", 'rb')
    #response = twitter.upload_media(media=image)
    #media_id = [response['media_id']]
    twitter.update_status(status=message)#, media_ids=media_id)
    print("Tweeted: %s" % message)

def set_pin_state():
    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(START_PIN, GPIO.IN)
    GPIO.setup(DATA_PIN, GPIO.IN)
    GPIO.setup(CLOCK_PIN, GPIO.IN)
    
    GPIO.setup(ALIVE_PIN1, GPIO.OUT)
    GPIO.output(ALIVE_PIN1, 1)
    GPIO.setup(ALIVE_PIN2, GPIO.OUT)
    GPIO.output(ALIVE_PIN2, 0)

def shutdown_pin_state():
    GPIO.output(ALIVE_PIN1, 0)
    GPIO.output(ALIVE_PIN2, 1)

def get_battery_voltage():
    # Receive and assemble the 16-bit value (MSB first)
    received_value = 0
    GPIO.wait_for_edge(START_PIN, GPIO.FALLING)
    for i in range(8):
        GPIO.wait_for_edge(CLOCK_PIN, GPIO.RISING)
        # Read the data bit from the DATA_PIN and update the received_value
        bit = GPIO.input(DATA_PIN)
        received_value = (received_value << 1) | bit# Wait for the clock to go low
        #print(bit, end="")
    return received_value

def get_average_battery_voltage():

    battery_voltages = []
    for i in range (5):
        battery_voltage = get_battery_voltage()
        #print(" " + str(battery_voltage))
        battery_voltages.append(battery_voltage)
    sorted_voltages = sorted(battery_voltages)
    #print(sorted_voltages)
    middle_idx = len(sorted_voltages) // 2
    median_value = (sorted_voltages[middle_idx - 1] + sorted_voltages[middle_idx]) / 2
    #print("The median value is:", median_value)
    median_value = round(median_value, 2)
    median_value = (median_value *2)/100
    return(median_value)

set_pin_state()
GPIO.output(ALIVE_PIN1, 1)
GPIO.output(ALIVE_PIN2, 1)

while True:
    
    time.sleep(10)
    now = datetime.datetime.now()
    dev_id = os.uname()[1]
    uptime = get_uptime()
    temp = get_temp()
    battery_voltage = get_average_battery_voltage()
    print(str(battery_voltage) + "V")

    try:
        if shutdown_start_hour <= now.hour or now.hour < shutdown_end_hour:
            event = " Night time shutdown...  "
            tweet_message(event)
            print("Shutdown the Raspberry Pi")
            shutdown_pin_state()
            os.system("sudo shutdown now")

        elif (float(temp) > 60):
            event = " Temperature shutdown...  "
            tweet_message(event)
            # Shutdown the Raspberry Pi
            shutdown_pin_state()
            os.system("sudo shutdown now")
    
        elif (float(battery_voltage) < 3.45):
            print("Low Battery Voltage Detected, getting results in 5 seconds")
            time.sleep(5)
            battery_voltage = get_average_battery_voltage()
            if (float(battery_voltage) < 3.45):
                event = " Low Battery Voltage Shutdown...  "
                time.sleep(2)
                tweet_message(event)
                shutdown_pin_state()
                os.system("sudo shutdown now")
            else:
                print("The low battery voltage was temporary")

        elif (now.minute == 34):
            event = "Normal"
            tweet_message(event)

        time.sleep(47)
        
    except:
        #twitter.update_status(status=message)
        print("An error with twython")
