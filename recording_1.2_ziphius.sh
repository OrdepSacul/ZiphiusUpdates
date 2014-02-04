#!/bin/bash
################################################
#	Estrutura de pastas ziphius
#
#    Media
#      |
#      |___ Thumbnails
#      |
#      |___ Videos
#      |
#      |___ Images
#
################################################

if [ "$1" = "rec" ]; then
#uvcdynctrl -d video0 --set="Focus, Auto" 0   #  ----set to for true
#uvcdynctrl -d video0 --set="White Balance Temperature, Auto" 0    # ---- set to 1 for true 
#uvcdynctrl -d video0 --set="Exposure, Auto" 0
#stamp=ziphius_$(date +%F_%T)
	raspivid -o /root/media/videos/$2.h264 -t 90000000 -w 1280 -h 720 --sharpness 50  1>/dev/null 2>&1
#	gerar preview p vid
fi

if [ "$1" = "screenshot" ]; then
	raspistill -t 0 -th 640:480:50 -o /root/media/images/$2.jpg -w 1280 -h 720 1>/dev/null 2>&1
#        raspistill -t 0 -th 640:360:50 -o /root/media/images/$2.jpg -w 1280 -h 720 1>/dev/null 2>&1
	jhead -st /root/media/thumbnails/$2.jpg /root/media/images/$2.jpg
fi

if [ "$1" = "panic" ]; then
	killall -INT raspivid raspistill gst-launch-0.10 mjpg_streamer 1>/dev/null 2>&1
fi
