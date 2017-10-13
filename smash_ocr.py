#!/usr/bin/python

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from PIL import Image#, ImageOps, ImageFilter
import subprocess as sp
import cv2
import os
import re

################################################
############## Global Parameters ###############
################################################

YTDL_BIN = "youtube-dl"
FFMPEG_BIN = "ffmpeg"
# the ocr program uses these files for input/output
OUTPUT_DIR = 'output'

SKIP_OCR_THRESH = 0.01

# Global variable to store previous frame
previous_frame_global = None
previous_damage_global = 0
differences = [] # debugging

################################################
######### Video Downloading Functions ##########
################################################


def download_video(videoID, start, duration):
    # Use youtube-dl to get the true url of the video
    videoURL = "https://www.youtube.com/watch?v=" + videoID
    command = [YTDL_BIN,
               "-f",
               "22/best",
               "--get-url",
               videoURL]
    sys.stdout.flush()

    p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout_data, stderr_data = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr_data)
    videoURL = stdout_data.strip()

    # prepare_video_directory(videoID)
    # Use ffmpeg to download the video
    command = [FFMPEG_BIN,
            "-y", # Overwrite files
            "-ss", str(start), # Start time
            "-i", videoURL, # Input - url
            "-t", str(duration), # Duration of stream to copy
            "-c:v", "copy", "-c:a", "copy", # No idea, yt stuff
            OUTPUT_DIR + '/' + videoID + ".mp4"] # Output
    sys.stdout.flush()

    p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout_data, stderr_data = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr_data)


def crop_video(videoID, CROP):
    crop = ":".join(str(x) for x in CROP)
    # prepare_video_directory(videoID)
    # Use ffmpeg to download the video
    command = [FFMPEG_BIN,
            "-y", # Overwrite files
            "-i", OUTPUT_DIR + '/' + videoID + '.mp4',
            "-vf","crop="+crop,
            OUTPUT_DIR + '/' + "smash.mp4"] # Output
    sys.stdout.flush()

    p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout_data, stderr_data = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr_data)


################################################
####### Image Transformation Functions #########
################################################

def binarize(image, level = 127):
    return cv2.threshold(image, level, 255, cv2.THRESH_BINARY)[1]

def img_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def img_pre_process(image_arr):
    bin_img = img_grayscale(image_arr)
    bin_img = binarize(bin_img, 211)
    return bin_img


# OpenCV stores image colors as BGR instead of what matplotlib expects: RGB
# This function allows easy plotting of OpenCV images
def show_img(image, swap_colors = True):
    if len(image.shape) == 3 and image.shape[2] == 3:
        if swap_colors:
            plt.imshow(image[:,:,[2,1,0]])
        else:
            plt.imshow(image[:,:,:])
    else:
        plt.imshow(image, cmap = cm.Greys_r)


################################################
############### OCR Functions ##################
################################################

def plz():
    return differences
# Find the active chord for each frame
def vidcap_to_frame_damage(vidcap, video_fps, nb_frames = -1):
    if nb_frames == -1:
        nb_frames = int(vidcap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
    frame_damages = []
    final_frame = int(nb_frames)
    for i in range(final_frame - 1):
        success,image = vidcap.read()
        frame_damages.append(get_active_damage(image))
    return frame_damages

# Find the active chord for a given frame
def get_active_damage(image):
    global previous_damage_global 
    pre_proc = img_pre_process(image)
    image_ocr(pre_proc)
    
    return previous_damage_global,differences

def image_ocr(image_arr):
    global previous_damage_global 
    global previous_frame_global 
    global differences
    if previous_frame_global is not None:
        assert image_arr.shape == previous_frame_global.shape, "Frames have different dimensions." #should never happen
        total_values = image_arr.shape[0]*image_arr.shape[1]
        difference = count_differences(image_arr, previous_frame_global)
        differences.append(difference)
        if difference / float(total_values) < SKIP_OCR_THRESH:
            return # current frame very similar to previous. No need to rerun OCR

    # Idk how to do it in memory yet :/
    imagePath = "the_image.png"
    cv2.imwrite(imagePath,image_arr)

    # Obtain yt link
    ocrCmd = ["tesseract",imagePath, "stdout", "-psm","7", "digits"]
    p = sp.Popen(ocrCmd, stdin=sp.PIPE, stdout=sp.PIPE)
    out, err = p.communicate()

    damage = onlyDigits(out)
    if damage == '':
        return previous_frame_global

    damage = abs(int(float(damage)))
    
    previous_frame_global = image_arr
    previous_damage_global = damage

    

################################################
############## Utility functions ###############
################################################

# Reads n frames from the OpenCV VideoCapture object.
def skip_frames(vidcap, n):
    count = 0
    while count < n:
        vidcap.read()
        count += 1

def count_differences(arr1, arr2):
    count = 0
    D0, D1 = arr1.shape
    for i in range(D0):
        for j in range(D1):
                if arr1[i,j] != arr2[i,j]:
                    count += 1
    return count

def onlyDigits(number):
    number = re.sub('\s+','', number)
    number = re.sub('\D' ,'', number)
    return number
