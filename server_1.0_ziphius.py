#!/usr/bin/env python

# extra modules:
# Firmata: https://github.com/lupeke/python-firmat (DEPRECATED!) #####
# ####################################################################
# Firmata : https://github.com/tino/pyFirmata.git (dependency: apt-get install python-serial)
# OSC bindings: http://das.nasophon.de/pyliblo/ 


import liblo, pyfirmata, sys, re, time, datetime, os, glob, subprocess, threading, statvfs #firmata
from pyfirmata import Arduino, util

#Globals

### OSC #################################
defaultListenPort = 5555
defaultReplyPort = 5556
target = ''
targetURL = ''
connected = False
startRecording = 0
isRecording = 0
takePic = 0
picTaken = 0
batteryLevel = 0
timestamp = "derp"
dateUpdated = False
#########################################

### GENERAL #############################
#used for checking free space (use in recording path?)
DEFAULT_ROOT_PATH = '/root/media/'
DEFAULT_IMAGES_PATH = '/root/media/images/'
DEFAULT_VIDEOS_PATH = '/root/media/videos/'
freeDiskPercentage = 0
videosPercentage = 0
imagesPercentage = 0
#########################################

### pyFirmata ###########################
# PINS: Digital outputs por PWM para simular um sinal analogico
#########################################
serialPort = '/dev/ttyAMA0' #use dmesg to check
BATTERY_LEVEL_PIN = 'a:4:i' #18?? 4 nao e analog
CAMERA_PIN = 'd:8:s'
LEFT_MOTOR_PIN = 'd:11:s'
RIGHT_MOTOR_PIN = 'd:12:s'
FLASH_LIGHT_PIN = 'd:6:p'
MOODLIGHT_RED_PIN = 'd:9:p'
MOODLIGHT_GREEN_PIN = 'd:5:p'
MOODLIGHT_BLUE_PIN = 'd:3:p'
MOTOR_MAX_VALUE = 170
MOTOR_MIN_VALUE = 8
CAMERA_MAX_VALUE = 155
CAMERA_MIN_VALUE = 17 
BATTERY_MIN = 0.5
BATTERY_MAX = 0.65
#########################################
# returns size of a directory in bytes
def directory_size(directory):
    dir_size = 0

    for (path, dirs, files) in os.walk(directory):
        for file in files:
            filename = os.path.join(path, file)
            dir_size += os.path.getsize(filename)
    return dir_size

# returns free available disk size in MB
def update_free_space():
    global freeDiskPercentage
    stats = os.statvfs(DEFAULT_ROOT_PATH)

    freeSpace = int(stats.f_bsize*stats.f_blocks)
    occupiedSpace = directory_size(DEFAULT_ROOT_PATH)
    occupiedImages = directory_size(DEFAULT_IMAGES_PATH)
    occupiedVideos = directory_size(DEFAULT_VIDEOS_PATH)

    freeDiskPercentage = (freeSpace*100) / (freeSpace+occupiedSpace)
    imagesPercentage = (occupiedImages*100) / (freeSpace+occupiedSpace)
    videosPercentage = (occupiedVideos*100) / (freeSpace+occupiedSpace)

#    if not totalSpace == (freeSpace-occupiedSpace):
#        totalSpace = freeSpace-occupiedSpace
    print '%i%% free. Free bytes: %i Occupied: %i Images: %i Videos: %i' % (freeDiskPercentage, freeSpace, occupiedSpace, occupiedImages, occupiedVideos) # imagesPercentage, videosPercentage)

# resets timeout for the present time
def resetTimeout():
    global lastTime
    lastTime = time.time()

# REPLACES HANDSHAKE CALLBACK METHOD!
# sets the new target adress depending on connected client
def setNewTarget(newTargetUrl):
    ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', newTargetUrl)
    global target
    try:
        target = liblo.Address(ip[0],defaultReplyPort)
    except liblo.AddressError, err:
        print str(err)
        sys.exit()
    global targetURL
    targetURL = newTargetUrl
    print 'changed target IP to ', ip[0]

#returns a value between 0 and 1 for the value passed as argument. result will vary according to max and min battery values.
def adjustBatteryLevel(oldLevel):
    return float( ( oldLevel - BATTERY_MIN ) * ( 1 / ( BATTERY_MAX - BATTERY_MIN ) ) )

# function to handle recording
def handleRec():
    global isRecording
    global startRecording
    while True:
        if startRecording == 1 and isRecording == 0:
#            processes = subprocess.Popen(['ps', 'x'], stdout=subprocess.PIPE).communicate()[0]
            processes = subprocess.Popen(['ps', 'x', '|', 'grep', 'raspivid'], shell=True, stdout=subprocess.PIPE).communicate()[0]
            if "raspivid" not in processes:
                st = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d_%H%M%S')
                os.system('./recording_1.0_ziphius.sh rec '+'zi'+st+' & 1>/dev/null 2>&1')
                isRecording = 1
            else:
                isRecording = 1
#            print processes
        elif startRecording == 0 and isRecording == 1:
            processes = subprocess.Popen(['ps', 'x', '|', 'grep', 'raspivid'], shell=True, stdout=subprocess.PIPE).communicate()[0]
            if "raspivid" in processes:
                os.system('./recording_1.0_ziphius.sh stream & 1>/dev/null 2>&1')
                isRecording = 0
                update_free_space()
#                os.system('ffmpeg -loglevel panic -itsoffset -105 -i '+timestamp+'.h264 -vcodec mjpeg -vframes 1 -an -f rawvideo -s 640x360 -y '+timestamp+'.jpg') #testing
#                os.system('MP4Box -add '+timestamp+'.h264 '+timestamp+'.mp4') #testing/takes a long time
            else:
                isRecording = 0
        time.sleep(0.1)     

# funtion to handle picture capture
def handlePic():
    global picTaken
    global takePic
    global timestamp
    while True:
        if takePic == 1 and picTaken == 0:
            processes = subprocess.Popen(['ps', 'x', '|', 'grep', 'raspistill'], shell=True, stdout=subprocess.PIPE).communicate()[0]
            if "raspistill" not in processes:
                picname = timestamp
                st = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d_%H%M%S')
                os.system('./recording_1.0_ziphius.sh screenshot '+'zi'+st+' 1>/dev/null 2>&1')
#		os.system('./recording_1.0_ziphius.sh screenshot '+timestamp+' 1>/dev/null 2>&1')
                picTaken = 1
                print 'started taking pic'
            elif "raspistill" in processes:
                picTaken = 1
                print 'taking pic as we speak'
        elif takePic == 0 and picTaken == 1:
            picTaken = 0
            print 'finished taking pic'
            update_free_space()
        time.sleep(0.1)


#IMPORTANT: Change raspberry pi's TZ with "dpkg-reconfigure tzdata" (EUROPE/Lisbon) 
#Receives total seconds from client and sets ziphius date
# to be passed to raspberry with a strict format: "17 OCT 2013 11:23:00" day MONTH(with 3 letters) year hour:minute:second
def changeDate(seconds):
    global dateUpdated
    struct = time.localtime(seconds)
    ndate = time.strftime("%d %b %Y %H:%M:%S", struct)
    success = os.system('sudo date --set=\"'+ndate+'\" 1>/dev/null 2>&1')
    if success == 0:
        dateUpdated = True
        print "date set successfully!"
    else:
        print "date not set!"
    


#to-do: create function, sending values received to Arduino using firmata
# funtion taking 7 values: cam pos, left motor, right motor, flash led, mood led ( R, G, B)
def signal_callback(path, args, types, src):
    secs, cam, joyX, joyY, flashLed, moodR, moodG, moodB, video, photo = args
    global startRecording, takePic, picTaken, isRecording
    global targetURL, batteryLevel, timestamp
    if src.get_url() != targetURL:
        setNewTarget(src.get_url())
    if not dateUpdated:
        changeDate(secs)
#    print "received message '%s' with arguments '%f', '%f', '%f', '%f', '%f', '%f', '%f', '%i', '%i' from %s" % (path, cam, joyX, joyY, flashLed, moodR, moodG, moodB, video, photo, src.get_url())
    camTilt = cameraValues(cam) #thread?
    camPin.write(camTilt)
    motors = motorValues(joyX,joyY) #criar thread?
    leftMotorPin.write(motors[0])
    rightMotorPin.write(motors[1])
#    print 'Left: %f  || Right: %f\n' % (motors[0],motors[1])
    flashPin.write(flashLed)
    moodPinR.write(moodR)
    moodPinG.write(moodG)
    moodPinB.write(moodB)
    startRecording = video
    takePic = photo
#    timestamp = stamp #NOT RECIEVING STRING!!!
#    print timestamp
#    batteryLevel = float(batteryPin.read())
#    batteryLevel = 0.6
#    liblo.send(target, "/state", adjustBatteryLevel(batteryLevel), isRecording, picTaken)
#    liblo.send(target, "/state", batteryLevel, video, photo)
#    print "sent values: '%f', '%i', '%i' " % (batteryLevel, isRecording, picTaken)


# DEPRECATED
# handshake function to acknowlege a connection
def handshake_callback(path, args, types, src):
    print "received message '%s' from %s" % (path, src.get_url())
    print 'saving info...' 
    ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', src.get_url())
    print 'got ip: ', ip[0]
    try:
        global target
	target = liblo.Address(ip[0],defaultReplyPort)
	liblo.send(target, "handshake", 'nice to meet you')
    except liblo.AddressError, err:
        print str(err)
        sys.exit()
    global connected
    connected = True
    print 'success!'


# using resetValues() serverside to reset 
# values range from 0 - 90 - 180 for motors/servo and 0 - 1 for leds
def resetValues():
    camPin.write(90)
    leftMotorPin.write(90)
    rightMotorPin.write(90)
    flashPin.write(0)
    moodPinR.write(1)
    moodPinG.write(0)
    moodPinB.write(0)
    print 'reset!'
	
def reset_callback():
    camPin.write(90)
    leftMotorPin.write(90)
    rightMotorPin.write(90)
    flashPin.write(0)
    moodPinR.write(1)
    moodPinG.write(0)
    moodPinB.write(0)
    print 'reset!'

#default fallback function
def fallback(path, args, types, src):
    print "got unknown message '%s' from '%s'" % (path, src.get_url())
    for a, t in zip(args, types):
        print "argument of type '%s': %f" % (t, a)

# custom funtion to clamp motor values
def clampMotor(value):
    return max(MOTOR_MIN_VALUE,min(value,MOTOR_MAX_VALUE))

# custom funtion to clamp camera values
def clampCamera(value):
    return max(CAMERA_MIN_VALUE,min(value,CAMERA_MAX_VALUE))

#funtion for calculating correct motor values from application joysticks
# todo: check clamping? (-1,-1 case)
def motorValues(axelX,axelY):
    x = float(axelX)
    y = float(axelY)

    left = float(y + x - (0.5*x*x*y) - (0.5*y*y*x))
    right = float(y - x - (0.5*x*x*y) + (0.5*y*y*x))
#    print 'Raw Left: %f  -  Raw Right: %f' % (left,right)
    left1 = float((left + 1) / 2)
    right1 = float((right + 1) / 2)
#    print 'Left: %f  -  Right: %f' % (left1,right1)
    return [clampMotor(int(left1 * 180)),clampMotor(int(right1 * 180))]

# funtion for calculating correct camera values from application joystick
def cameraValues(tilt):
    return clampCamera( int( ( tilt + 1 ) * 90 ) )

### INIT ####################################

#check free space for the first time
update_free_space()

# initializing Arduino board
print 'Setting up board...'
board = pyfirmata.Arduino(serialPort)
it = util.Iterator(board, 0.05) #object board, interval
it.start()
print 'Setup complete.'

# create server, listening on default port
try:
    server = liblo.Server(defaultListenPort)
    lastTime = time.time() # save time for disconnect detection purposes
except liblo.ServerError, err:
    print str(err)
    sys.exit()
	
# register method for taking camera, front, back, left and right motor values, all float between -1, 1
server.add_method("/signal", 'hfffffffii', signal_callback)

# register method for resetting values to default
server.add_method("/reset", None, reset_callback)

# register method for handshake
server.add_method("handshake", 's', handshake_callback)

#register method for unhandled messages
server.add_method(None, None, fallback)

#get control pins for camera, motors and leds
batteryPin = board.get_pin(BATTERY_LEVEL_PIN)
camPin = board.get_pin(CAMERA_PIN)
leftMotorPin = board.get_pin(LEFT_MOTOR_PIN)
rightMotorPin = board.get_pin(RIGHT_MOTOR_PIN)
flashPin = board.get_pin(FLASH_LIGHT_PIN)
moodPinR = board.get_pin(MOODLIGHT_RED_PIN)
moodPinG = board.get_pin(MOODLIGHT_GREEN_PIN)
moodPinB = board.get_pin(MOODLIGHT_BLUE_PIN)

# using iterator declared before, to prevent serial from overflowing
batteryPin.enable_reporting()

# get battery level for the first time
#batteryLevel = float(adjustBatteryLevel(batteryPin.read()))

#threads to handle image capture
vThread = threading.Thread(name='VideoThread', target = handleRec)
vThread.setDaemon(1)
vThread.start()
pThread = threading.Thread(name='PicThread', target = handlePic)
pThread.setDaemon(1)
pThread.start()
print 'Running threads: '+str(threading.enumerate())	
	
############################################
	
	
# loop and dispatch messages every 100ms
while True:
    try:
        if not server.recv(100):
            if (time.time()-lastTime) > 2:
                resetValues()
#        	 print 'disconnected, resetting values...'
        else:
            #resetTimeout()
            lastTime = time.time()

        if target:        
#            batteryLevel = float(batteryPin.read())
            batteryLevel = 0.6
#            liblo.send(target, "/state", adjustBatteryLevel(batteryLevel), isRecording, picTaken)
            printableBatteryLevel = adjustBatteryLevel(batteryLevel)
	    print 'State battery level: %.2f Free space: %i' % (printableBatteryLevel, freeDiskPercentage)
           
            liblo.send(target, "/state", adjustBatteryLevel(batteryLevel), isRecording, picTaken, int(freeDiskPercentage))
        time.sleep(0.1)
    except KeyboardInterrupt, err:
	print str(err)
	print 'exception caught, cleaning up...'
	server.free()
	#it._stop.set()
        board.exit()
	sys.exit(0)
