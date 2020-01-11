#!/usr/bin/env python

from os import system
import serial
import time
import subprocess
import tweepy
from tweepy.auth import OAuthHandler
from curses import ascii
from time import sleep
from ISStreamer.Streamer import Streamer


BUCKET_NAME = "GPS streamer"
BUCKET_KEY = "****"
ACCESS_KEY = "*****************************"
SECONDS_BETWEEN_READS = 10.0 #after testing set back to 60
TWITTER_STATUSUPDATE = "My bike is stolen follow it here: \n https://go.init.st/5w470cv"
SMSSEND = "AT+CMGS=\"+36204071023\"\r"
SMSTEXT = "Your Bike is stolen!"


def boot():
	subprocess.call("python GSM_PWRKEY.py", shell=True)
	sleep(5)
	ser = serial.Serial("/dev/ttyS0",115200)
	ser.write("AT+CPIN=****\r")
	sleep(2)
	ser.write("AT+CGNSPWR=1\r")
	sleep(2)


# Start PPPD
def openPPPD():
	# Check if PPPD is already running by looking at syslog output
	output1 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
	if "secondary DNS address" not in output1 and "locked" not in output1:
		while True:
			# Start the "fona" process
			subprocess.call("sudo pon fona", shell=True)
			sleep(2)
			subprocess.call("sudo route add -net 0.0.0.0 ppp0", shell=True)
			sleep(2)
			output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
			if "script failed" not in output2:
				break
	# Make sure the connection is working
	#while True:
	#	output2 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
	#	output3 = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -3", shell=True)
	#	if "secondary DNS address" in output2 or "secondary DNS address" in output3:
	return True

# Stop PPPD
def closePPPD():
	print "turning off cell connection"
	# Stop the "fona" process
	subprocess.call("sudo poff fona", shell=True)
	# Make sure connection was actually terminated
	#while True:
	#	output = subprocess.check_output("cat /var/log/syslog | grep pppd | tail -1", shell=True)
	#	if "Exit" in output:
	return True

def sendSMS():
	ser = serial.Serial("/dev/ttyS0",115200)
	
	ser.write("AT+CSCA=\"+36209300099\"\r")
	ser.write("AT+CMGF=1\r")
	ser.write("AT+CMGS=\"+36204071023\"\r")
	sleep(0.5)
	ser.write('Your bike is stolen!\r')
	sleep(0.5)
	ser.write(ascii.ctrl('z'))
	sleep(0.5)

def piisreadySMS():
	ser = serial.Serial("/dev/ttyS0",115200)
	
	ser.write("AT+CSCA=\"+36209300099\"\r")
	ser.write("AT+CMGF=1\r")
	ser.write("AT+CMGS=\"+36204071023\"\r")
	sleep(0.5)
	ser.write('The Pi is ready, GPS fix found, and ready to Stream!\r')
	sleep(0.5)
	ser.write(ascii.ctrl('z'))
	sleep(0.5)

def lostgpsSMS():
	ser = serial.Serial("/dev/ttyS0",115200)
	
	ser.write("AT+CSCA=\"+36209300099\"\r")
	ser.write("AT+CMGF=1\r")
	ser.write("AT+CMGS=\"+36204071023\"\r")
	sleep(0.5)
	ser.write('The Pi lost fix GPS!\r')
	sleep(0.5)
	ser.write(ascii.ctrl('z'))
	sleep(0.5)


def tweet():
	# Authenticate to Twitter
	auth = OAuthHandler("rgCWVMVJzQUyWVr8klOqgR9kH", "6pzc2ZgDYFr1ElfITTW3mLH31g4gC3UWTqQKzdIsgGTLKZtXRd")
	auth.set_access_token("2803691216-0pWIbkmWYVoTtveQnx0xT3nY3s8y9aF3Z5Fl0fq","BwTcLdYML88y0tnmq7Evgwn2mlqYMz5fDPosnFD9keeri")
	api = tweepy.API(auth)
	# test authentication
	api.update_status("My bike is stolen follow it here: \n https://go.init.st/5w470cv")


# Check for a GPS fix
def checkForFix(FIRSTFIX):
	print "checking for fix"
	# Start the serial connection
	ser = serial.Serial("/dev/ttyS0",115200)
	ser.write("AT+CGNSPWR=1\r")
	sleep(2)
	print "GPS is on"
	sleep(0.5)
	reply = ""
	# Ask for the navigation info parsed from NMEA sentence
	while True:
		while ser.inWaiting() > 0:
			reply = ser.read(ser.inWaiting())
		# Check if a fix was found
		if "+CGNSINF: 1,1," in reply:
			print "fix found"
			if FIRSTFIX:
				piisreadySMS()
				sleep(10)

			print reply
			return True
		# If a fix wasn't found, wait and try again
		if "+CGNSINF: 1,0," in reply:
			ser.write("AT+CGNSINF\r")
			print "still looking for fix"
			if FIRSTFIX == False:
				lostgpsSMS()
				sleep(3)
			sleep(30)
		else:
			ser.write("AT+CGNSINF\r")
			print reply
		sleep(2)


# Read the GPS data for Latitude and Longitude
def getCoordandSpeed():
	# Start the serial connection
	ser = serial.Serial("/dev/ttyS0",115200)
	ser.write("AT+CGNSINF\r")
	while True:
		response = ser.readline()
		if "+CGNSINF: 1," in response:
			# Split the reading by commas and return the parts referencing lat and long
			array = response.split(",")
			lat = array[3]
			print lat
			lon = array[4]
			alt = array[5]
			print lon
			speed = array[6]
			return (lat,lon,speed,alt)



def check(speedlog, val=2):
    move = 0
    for i in speedlog:
        if i > val:
            move=move+1
    if move > 3:
        return True


#sleep(50)
#boot()
FIRSTFIX = True
# Start the program by opening the cellular connection and creating a bucket for our data
if openPPPD():
	# Initialize the Initial State streamer
	streamer = Streamer(bucket_name=BUCKET_NAME, bucket_key=BUCKET_KEY, access_key=ACCESS_KEY, buffer_size=20)
	# Wait long enough for the request to complete
	sleep(10)
	while True:
		# Close the cellular connection
		if closePPPD():
			print "closing connection"
			sleep(2)
		# Make sure there's a GPS fix
		if checkForFix(FIRSTFIX):
			FIRSTFIX = False
			# Get lat and long
			if getCoordandSpeed():
				latitude, longitude, speed, altitude = getCoordandSpeed()
				coord = str(latitude) + "," + str(longitude)
				print coord
				print speed
				print altitude
				# Buffer the coordinates to be streamed
				streamer.log("Coordinates",coord)
				streamer.log("Speed",speed)
				streamer.log("Altitude", altitude)
				sleep(2)
				if openPPPD():
					print "streaming"
					streamer.flush()
					print "streaming complete"
					if closePPPD():
						print "closing connection"
				sleep(SECONDS_BETWEEN_READS/(float(speed)+1.0))
					

					



