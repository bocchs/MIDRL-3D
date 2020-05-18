#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: common.py
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>
# Modified: Amir Alansary <amiralansary@gmail.com>
# Modified: Athanasios Vlontzos <athanasiosvlontzos@gmail.com>
# Modified: Alex Bocchieri <abocchi2@jhu.edu>

import random
import time
import threading
import numpy as np
from tqdm import tqdm
import multiprocessing
from six.moves import queue

# from tensorpack import *
# from tensorpack.utils.stats import *
from tensorpack.utils import logger
# from tensorpack.callbacks import Triggerable
from tensorpack.callbacks.base import Callback
from tensorpack.utils.stats import StatCounter
from tensorpack.utils.utils import get_tqdm_kwargs
from tensorpack.utils.concurrency import (StoppableThread, ShareSessionThread)

import traceback
import sys
import statistics
import xlwt
from xlwt import Workbook

###############################################################################

def play_one_episode(env, func, render=False,agents=2):
    def predict(s,agents):
        """
        Run a full episode, mapping observation to action, WITHOUT 0.001 greedy.
    :returns sum of rewards
        """
        # pick action with best predicted Q-value
        acts=np.zeros((agents,))
        for i in range(0,agents):
            s[i]=s[i][None,:,:,:]
        q_values = func(*s)
        for i in range(0,agents):
            q_values[i] = q_values[i].flatten()
            acts[i] = np.argmax(q_values[i])

        return acts, q_values

    obs = env.reset()
    obs=list(obs)
    sum_r = np.zeros((agents,))
    filenames_list = []
    dist_error_pix_list = []
    dist_error_mm_list = []
    isOver=[False]*agents
    while True:
        acts, q_values = predict(obs,agents)
        obs,r, isOver, info = env.step(acts, q_values,isOver)
        obs=list(obs)
        if render:
            env.render()

        for i in range(0,agents):
            if not isOver[i]:
                sum_r[i] += r[i]
            if np.all(isOver):
                filenames_list.append(info['filename_{}'.format(i)])
                dist_error_pix_list.append(info['distErrorPix_{}'.format(i)])
                dist_error_mm_list.append(info['distErrorMM_{}'.format(i)])
        if np.all(isOver):
            return info['filename'], dist_error_pix_list, dist_error_mm_list, env.dice, env.iou, sum_r  #, env.landmark


###############################################################################

def play_n_episodes(player, predfunc, nr, render=False,agents=2):
    """wraps play_one_episode, playing a single episode at a time and logs results
    used when playing demos."""
    logger.info("Start Playing ... ")
    dists=np.zeros((nr,4))

    locs = np.zeros((nr,4)) # list of the last locations (x,y,z)
    logger.info("Start Playing ... ")

    wb = Workbook()

    heart_sheet = wb.add_sheet('heart')
    kidney_sheet = wb.add_sheet('kidney')
    troch_sheet = wb.add_sheet('trochanter')
    knee_sheet = wb.add_sheet('knee')
    all_sheet = wb.add_sheet('all')

    all_sheet.write(0,0,'Image')
    all_sheet.write(0,1,'Distance Error 3D (mm)')
    all_sheet.write(0,2,'Distance Error 3D (pixels)')
    all_sheet.write(0,3,'Dice 3D')
    all_sheet.write(0,4,'IoU 3D')
    all_row = 1
    heart_sheet.write(0,0,'Image')
    heart_sheet.write(0,1,'Distance Error 3D (mm)')
    heart_sheet.write(0,2,'Distance Error 3D (pixels)')
    heart_sheet.write(0,3,'Dice 3D')
    heart_sheet.write(0,4,'IoU 3D')
    heart_row = 1
    kidney_sheet.write(0,0,'Image')
    kidney_sheet.write(0,1,'Distance Error 3D (mm)')
    kidney_sheet.write(0,2,'Distance Error 3D (pixels)')
    kidney_sheet.write(0,3,'Dice 3D')
    kidney_sheet.write(0,4,'IoU 3D')
    kidney_row = 1
    troch_sheet.write(0,0,'Image')
    troch_sheet.write(0,1,'Distance Error 3D (mm)')
    troch_sheet.write(0,2,'Distance Error 3D (pixels)')
    troch_sheet.write(0,3,'Dice 3D')
    troch_sheet.write(0,4,'IoU 3D')
    troch_row = 1
    knee_sheet.write(0,0,'Image')
    knee_sheet.write(0,1,'Distance Error 3D (mm)')
    knee_sheet.write(0,2,'Distance Error 3D (pixels)')
    knee_sheet.write(0,3,'Dice 3D')
    knee_sheet.write(0,4,'IoU 3D')
    knee_row = 1



    kidney_in_dist_pix_list = []
    kidney_in_dist_mm_list = []
    kidney_in_dice_list = []
    kidney_in_iou_list = []

    kidney_opp_dist_pix_list = []
    kidney_opp_dist_mm_list = []
    kidney_opp_dice_list = []
    kidney_opp_iou_list = []

    kidney_F_dist_pix_list = []
    kidney_F_dist_mm_list = []
    kidney_F_dice_list = []
    kidney_F_iou_list = []

    kidney_W_dist_pix_list = []
    kidney_W_dist_mm_list = []
    kidney_W_dice_list = []
    kidney_W_iou_list = []

    kidney_t1_dist_pix_list = []
    kidney_t1_dist_mm_list = []
    kidney_t1_dice_list = []
    kidney_t1_iou_list = []

    kidney_t2_dist_pix_list = []
    kidney_t2_dist_mm_list = []
    kidney_t2_dice_list = []
    kidney_t2_iou_list = []

    kidney_all_dist_pix_list = []
    kidney_all_dist_mm_list = []
    kidney_all_dice_list = []
    kidney_all_iou_list = []



    troch_in_dist_pix_list = []
    troch_in_dist_mm_list = []
    troch_in_dice_list = []
    troch_in_iou_list = []

    troch_opp_dist_pix_list = []
    troch_opp_dist_mm_list = []
    troch_opp_dice_list = []
    troch_opp_iou_list = []

    troch_F_dist_pix_list = []
    troch_F_dist_mm_list = []
    troch_F_dice_list = []
    troch_F_iou_list = []

    troch_W_dist_pix_list = []
    troch_W_dist_mm_list = []
    troch_W_dice_list = []
    troch_W_iou_list = []

    troch_t1_dist_pix_list = []
    troch_t1_dist_mm_list = []
    troch_t1_dice_list = []
    troch_t1_iou_list = []

    troch_t2_dist_pix_list = []
    troch_t2_dist_mm_list = []
    troch_t2_dice_list = []
    troch_t2_iou_list = []

    troch_all_dist_pix_list = []
    troch_all_dist_mm_list = []
    troch_all_dice_list = []
    troch_all_iou_list = []



    heart_in_dist_pix_list = []
    heart_in_dist_mm_list = []
    heart_in_dice_list = []
    heart_in_iou_list = []

    heart_opp_dist_pix_list = []
    heart_opp_dist_mm_list = []
    heart_opp_dice_list = []
    heart_opp_iou_list = []

    heart_F_dist_pix_list = []
    heart_F_dist_mm_list = []
    heart_F_dice_list = []
    heart_F_iou_list = []

    heart_W_dist_pix_list = []
    heart_W_dist_mm_list = []
    heart_W_dice_list = []
    heart_W_iou_list = []

    heart_t1_dist_pix_list = []
    heart_t1_dist_mm_list = []
    heart_t1_dice_list = []
    heart_t1_iou_list = []

    heart_t2_dist_pix_list = []
    heart_t2_dist_mm_list = []
    heart_t2_dice_list = []
    heart_t2_iou_list = []

    heart_all_dist_pix_list = []
    heart_all_dist_mm_list = []
    heart_all_dice_list = []
    heart_all_iou_list = []



    knee_in_dist_pix_list = []
    knee_in_dist_mm_list = []
    knee_in_dice_list = []
    knee_in_iou_list = []

    knee_opp_dist_pix_list = []
    knee_opp_dist_mm_list = []
    knee_opp_dice_list = []
    knee_opp_iou_list = []

    knee_F_dist_pix_list = []
    knee_F_dist_mm_list = []
    knee_F_dice_list = []
    knee_F_iou_list = []

    knee_W_dist_pix_list = []
    knee_W_dist_mm_list = []
    knee_W_dice_list = []
    knee_W_iou_list = []

    knee_t1_dist_pix_list = []
    knee_t1_dist_mm_list = []
    knee_t1_dice_list = []
    knee_t1_iou_list = []

    knee_t2_dist_pix_list = []
    knee_t2_dist_mm_list = []
    knee_t2_dice_list = []
    knee_t2_iou_list = []

    knee_all_dist_pix_list = []
    knee_all_dist_mm_list = []
    knee_all_dice_list = []
    knee_all_iou_list = []


    all_dist_pix_list = []
    all_dist_mm_list = []
    all_dice_list = []
    all_iou_list = []


    for k in range(nr):
        filename_ra, distance_error_pix_ra, distance_error_mm_ra, dice_ra, iou_ra, sum_r \
                                                                 = play_one_episode(player,
                                                                    predfunc,
                                                                    render=render,agents=agents)


        landmark_ra = ["kidney", "trochanter", "heart", "knee"]

        for i in range(0,agents):
            landmark = landmark_ra[i]
            iou = iou_ra[i]
            dice = dice_ra[i]
            distance_error_mm = distance_error_mm_ra[i]
            distance_error_pix = distance_error_pix_ra[i]
            filename = filename_ra[i]

            print(filename) 
            print("dist mm = " + str(distance_error_mm))
            print("dist pix = " + str(distance_error_pix))
            print("dice = " + str(dice))
            print("iou = " + str(iou))
            print()

            all_sheet.write(all_row,0,filename)
            all_sheet.write(all_row,1,distance_error_mm)
            all_sheet.write(all_row,2,distance_error_pix)
            all_sheet.write(all_row,3,dice)
            all_sheet.write(all_row,4,iou)
            all_row += 1
            all_dist_pix_list.append(distance_error_pix)
            all_dist_mm_list.append(distance_error_mm)
            all_dice_list.append(dice)
            all_iou_list.append(iou)

            



            if landmark == "heart":
                heart_sheet.write(heart_row,0,filename)
                heart_sheet.write(heart_row,1,distance_error_mm)
                heart_sheet.write(heart_row,2,distance_error_pix)
                heart_sheet.write(heart_row,3,dice)
                heart_sheet.write(heart_row,4,iou)
                heart_row += 1
                heart_all_dist_pix_list.append(distance_error_pix)
                heart_all_dist_mm_list.append(distance_error_mm)
                heart_all_dice_list.append(dice)
                heart_all_iou_list.append(iou)
                if "_in" in filename:
                    heart_in_dist_pix_list.append(distance_error_pix)
                    heart_in_dist_mm_list.append(distance_error_mm)
                    heart_in_dice_list.append(dice)
                    heart_in_iou_list.append(iou)
                elif "_opp" in filename:
                    heart_opp_dist_pix_list.append(distance_error_pix)
                    heart_opp_dist_mm_list.append(distance_error_mm)
                    heart_opp_dice_list.append(dice)
                    heart_opp_iou_list.append(iou)
                elif "_F" in filename:
                    heart_F_dist_pix_list.append(distance_error_pix)
                    heart_F_dist_mm_list.append(distance_error_mm)
                    heart_F_dice_list.append(dice)
                    heart_F_iou_list.append(iou)
                elif "_W" in filename:
                    heart_W_dist_pix_list.append(distance_error_pix)
                    heart_W_dist_mm_list.append(distance_error_mm)
                    heart_W_dice_list.append(dice)
                    heart_W_iou_list.append(iou)
                elif "_t1" in filename:
                    heart_t1_dist_pix_list.append(distance_error_pix)
                    heart_t1_dist_mm_list.append(distance_error_mm)
                    heart_t1_dice_list.append(dice)
                    heart_t1_iou_list.append(iou)
                elif "_t2" in filename:
                    heart_t2_dist_pix_list.append(distance_error_pix)
                    heart_t2_dist_mm_list.append(distance_error_mm)
                    heart_t2_dice_list.append(dice)
                    heart_t2_iou_list.append(iou)
                else:
                    print("unknown image type, exiting...")
                    sys.exit()
            elif landmark == "kidney":
                kidney_sheet.write(kidney_row,0,filename)
                kidney_sheet.write(kidney_row,1,distance_error_mm)
                kidney_sheet.write(kidney_row,2,distance_error_pix)
                kidney_sheet.write(kidney_row,3,dice)
                kidney_sheet.write(kidney_row,4,iou)
                kidney_row += 1
                kidney_all_dist_pix_list.append(distance_error_pix)
                kidney_all_dist_mm_list.append(distance_error_mm)
                kidney_all_dice_list.append(dice)
                kidney_all_iou_list.append(iou)
                if "_in" in filename:
                    kidney_in_dist_pix_list.append(distance_error_pix)
                    kidney_in_dist_mm_list.append(distance_error_mm)
                    kidney_in_dice_list.append(dice)
                    kidney_in_iou_list.append(iou)
                elif "_opp" in filename:
                    kidney_opp_dist_pix_list.append(distance_error_pix)
                    kidney_opp_dist_mm_list.append(distance_error_mm)
                    kidney_opp_dice_list.append(dice)
                    kidney_opp_iou_list.append(iou)
                elif "_F" in filename:
                    kidney_F_dist_pix_list.append(distance_error_pix)
                    kidney_F_dist_mm_list.append(distance_error_mm)
                    kidney_F_dice_list.append(dice)
                    kidney_F_iou_list.append(iou)
                elif "_W" in filename:
                    kidney_W_dist_pix_list.append(distance_error_pix)
                    kidney_W_dist_mm_list.append(distance_error_mm)
                    kidney_W_dice_list.append(dice)
                    kidney_W_iou_list.append(iou)
                elif "_t1" in filename:
                    kidney_t1_dist_pix_list.append(distance_error_pix)
                    kidney_t1_dist_mm_list.append(distance_error_mm)
                    kidney_t1_dice_list.append(dice)
                    kidney_t1_iou_list.append(iou)
                elif "_t2" in filename:
                    kidney_t2_dist_pix_list.append(distance_error_pix)
                    kidney_t2_dist_mm_list.append(distance_error_mm)
                    kidney_t2_dice_list.append(dice)
                    kidney_t2_iou_list.append(iou)
                else:
                    print("unknown image type, exiting...")
                    sys.exit()
            elif landmark == "trochanter":
                troch_sheet.write(troch_row,0,filename)
                troch_sheet.write(troch_row,1,distance_error_mm)
                troch_sheet.write(troch_row,2,distance_error_pix)
                troch_sheet.write(troch_row,3,dice)
                troch_sheet.write(troch_row,4,iou)
                troch_row += 1
                troch_all_dist_pix_list.append(distance_error_pix)
                troch_all_dist_mm_list.append(distance_error_mm)
                troch_all_dice_list.append(dice)
                troch_all_iou_list.append(iou)
                if "_in" in filename:
                    troch_in_dist_pix_list.append(distance_error_pix)
                    troch_in_dist_mm_list.append(distance_error_mm)
                    troch_in_dice_list.append(dice)
                    troch_in_iou_list.append(iou)
                elif "_opp" in filename:
                    troch_opp_dist_pix_list.append(distance_error_pix)
                    troch_opp_dist_mm_list.append(distance_error_mm)
                    troch_opp_dice_list.append(dice)
                    troch_opp_iou_list.append(iou)
                elif "_F" in filename:
                    troch_F_dist_pix_list.append(distance_error_pix)
                    troch_F_dist_mm_list.append(distance_error_mm)
                    troch_F_dice_list.append(dice)
                    troch_F_iou_list.append(iou)
                elif "_W" in filename:
                    troch_W_dist_pix_list.append(distance_error_pix)
                    troch_W_dist_mm_list.append(distance_error_mm)
                    troch_W_dice_list.append(dice)
                    troch_W_iou_list.append(iou)
                elif "_t1" in filename:
                    troch_t1_dist_pix_list.append(distance_error_pix)
                    troch_t1_dist_mm_list.append(distance_error_mm)
                    troch_t1_dice_list.append(dice)
                    troch_t1_iou_list.append(iou)
                elif "_t2" in filename:
                    troch_t2_dist_pix_list.append(distance_error_pix)
                    troch_t2_dist_mm_list.append(distance_error_mm)
                    troch_t2_dice_list.append(dice)
                    troch_t2_iou_list.append(iou)
                else:
                    print("unknown image type, exiting...")
                    sys.exit()
            elif landmark == "knee":
                knee_sheet.write(knee_row,0,filename)
                knee_sheet.write(knee_row,1,distance_error_mm)
                knee_sheet.write(knee_row,2,distance_error_pix)
                knee_sheet.write(knee_row,3,dice)
                knee_sheet.write(knee_row,4,iou)
                knee_row += 1
                knee_all_dist_pix_list.append(distance_error_pix)
                knee_all_dist_mm_list.append(distance_error_mm)
                knee_all_dice_list.append(dice)
                knee_all_iou_list.append(iou)
                if "_in" in filename:
                    knee_in_dist_pix_list.append(distance_error_pix)
                    knee_in_dist_mm_list.append(distance_error_mm)
                    knee_in_dice_list.append(dice)
                    knee_in_iou_list.append(iou)
                elif "_opp" in filename:
                    knee_opp_dist_pix_list.append(distance_error_pix)
                    knee_opp_dist_mm_list.append(distance_error_mm)
                    knee_opp_dice_list.append(dice)
                    knee_opp_iou_list.append(iou)
                elif "_F" in filename:
                    knee_F_dist_pix_list.append(distance_error_pix)
                    knee_F_dist_mm_list.append(distance_error_mm)
                    knee_F_dice_list.append(dice)
                    knee_F_iou_list.append(iou)
                elif "_W" in filename:
                    knee_W_dist_pix_list.append(distance_error_pix)
                    knee_W_dist_mm_list.append(distance_error_mm)
                    knee_W_dice_list.append(dice)
                    knee_W_iou_list.append(iou)
                elif "_t1" in filename:
                    knee_t1_dist_pix_list.append(distance_error_pix)
                    knee_t1_dist_mm_list.append(distance_error_mm)
                    knee_t1_dice_list.append(dice)
                    knee_t1_iou_list.append(iou)
                elif "_t2" in filename:
                    knee_t2_dist_pix_list.append(distance_error_pix)
                    knee_t2_dist_mm_list.append(distance_error_mm)
                    knee_t2_dice_list.append(dice)
                    knee_t2_iou_list.append(iou)
                else:
                    print("unknown image type, exiting...")
                    sys.exit()
            else:
                print("UNKNOWN LANDMARK, exiting...")
                sys.exit()


    if agents >= 1:
        kidney_in_dist_pix_mean = statistics.mean(kidney_in_dist_pix_list)
        kidney_in_dist_mm_mean = statistics.mean(kidney_in_dist_mm_list)
        kidney_in_dice_mean = statistics.mean(kidney_in_dice_list)
        kidney_in_iou_mean = statistics.mean(kidney_in_iou_list)
        kidney_in_dist_pix_stdev = statistics.stdev(kidney_in_dist_pix_list)
        kidney_in_dist_mm_stdev = statistics.stdev(kidney_in_dist_mm_list)
        kidney_in_dice_stdev = statistics.stdev(kidney_in_dice_list)
        kidney_in_iou_stdev = statistics.stdev(kidney_in_iou_list)

        kidney_opp_dist_pix_mean = statistics.mean(kidney_opp_dist_pix_list)
        kidney_opp_dist_mm_mean = statistics.mean(kidney_opp_dist_mm_list)
        kidney_opp_dice_mean = statistics.mean(kidney_opp_dice_list)
        kidney_opp_iou_mean = statistics.mean(kidney_opp_iou_list)
        kidney_opp_dist_pix_stdev = statistics.stdev(kidney_opp_dist_pix_list)
        kidney_opp_dist_mm_stdev = statistics.stdev(kidney_opp_dist_mm_list)
        kidney_opp_dice_stdev = statistics.stdev(kidney_opp_dice_list)
        kidney_opp_iou_stdev = statistics.stdev(kidney_opp_iou_list)

        kidney_F_dist_pix_mean = statistics.mean(kidney_F_dist_pix_list)
        kidney_F_dist_mm_mean = statistics.mean(kidney_F_dist_mm_list)
        kidney_F_dice_mean = statistics.mean(kidney_F_dice_list)
        kidney_F_iou_mean = statistics.mean(kidney_F_iou_list)
        kidney_F_dist_pix_stdev = statistics.stdev(kidney_F_dist_pix_list)
        kidney_F_dist_mm_stdev = statistics.stdev(kidney_F_dist_mm_list)
        kidney_F_dice_stdev = statistics.stdev(kidney_F_dice_list)
        kidney_F_iou_stdev = statistics.stdev(kidney_F_iou_list)

        kidney_W_dist_pix_mean = statistics.mean(kidney_W_dist_pix_list)
        kidney_W_dist_mm_mean = statistics.mean(kidney_W_dist_mm_list)
        kidney_W_dice_mean = statistics.mean(kidney_W_dice_list)
        kidney_W_iou_mean = statistics.mean(kidney_W_iou_list)
        kidney_W_dist_pix_stdev = statistics.stdev(kidney_W_dist_pix_list)
        kidney_W_dist_mm_stdev = statistics.stdev(kidney_W_dist_mm_list)
        kidney_W_dice_stdev = statistics.stdev(kidney_W_dice_list)
        kidney_W_iou_stdev = statistics.stdev(kidney_W_iou_list)

        kidney_t1_dist_pix_mean = statistics.mean(kidney_t1_dist_pix_list)
        kidney_t1_dist_mm_mean = statistics.mean(kidney_t1_dist_mm_list)
        kidney_t1_dice_mean = statistics.mean(kidney_t1_dice_list)
        kidney_t1_iou_mean = statistics.mean(kidney_t1_iou_list)
        kidney_t1_dist_pix_stdev = statistics.stdev(kidney_t1_dist_pix_list)
        kidney_t1_dist_mm_stdev = statistics.stdev(kidney_t1_dist_mm_list)
        kidney_t1_dice_stdev = statistics.stdev(kidney_t1_dice_list)
        kidney_t1_iou_stdev = statistics.stdev(kidney_t1_iou_list)

        kidney_t2_dist_pix_mean = statistics.mean(kidney_t2_dist_pix_list)
        kidney_t2_dist_mm_mean = statistics.mean(kidney_t2_dist_mm_list)
        kidney_t2_dice_mean = statistics.mean(kidney_t2_dice_list)
        kidney_t2_iou_mean = statistics.mean(kidney_t2_iou_list)
        kidney_t2_dist_pix_stdev = statistics.stdev(kidney_t2_dist_pix_list)
        kidney_t2_dist_mm_stdev = statistics.stdev(kidney_t2_dist_mm_list)
        kidney_t2_dice_stdev = statistics.stdev(kidney_t2_dice_list)
        kidney_t2_iou_stdev = statistics.stdev(kidney_t2_iou_list)


        kidney_all_dist_pix_mean = statistics.mean(kidney_all_dist_pix_list)
        kidney_all_dist_mm_mean = statistics.mean(kidney_all_dist_mm_list)
        kidney_all_dice_mean = statistics.mean(kidney_all_dice_list)
        kidney_all_iou_mean = statistics.mean(kidney_all_iou_list)
        kidney_all_dist_pix_stdev = statistics.stdev(kidney_all_dist_pix_list)
        kidney_all_dist_mm_stdev = statistics.stdev(kidney_all_dist_mm_list)
        kidney_all_dice_stdev = statistics.stdev(kidney_all_dice_list)
        kidney_all_iou_stdev = statistics.stdev(kidney_all_iou_list)

        kidney_sheet.write(kidney_row,0,"mean in")
        kidney_sheet.write(kidney_row,1,kidney_in_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_in_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_in_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_in_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev in")
        kidney_sheet.write(kidney_row,1,kidney_in_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_in_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_in_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_in_iou_stdev)
        kidney_row += 1

        kidney_sheet.write(kidney_row,0,"mean opp")
        kidney_sheet.write(kidney_row,1,kidney_opp_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_opp_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_opp_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_opp_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev opp")
        kidney_sheet.write(kidney_row,1,kidney_opp_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_opp_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_opp_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_opp_iou_stdev)
        kidney_row += 1


        kidney_sheet.write(kidney_row,0,"mean F")
        kidney_sheet.write(kidney_row,1,kidney_F_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_F_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_F_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_F_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev F")
        kidney_sheet.write(kidney_row,1,kidney_F_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_F_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_F_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_F_iou_stdev)
        kidney_row += 1

        kidney_sheet.write(kidney_row,0,"mean W")
        kidney_sheet.write(kidney_row,1,kidney_W_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_W_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_W_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_W_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev W")
        kidney_sheet.write(kidney_row,1,kidney_W_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_W_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_W_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_W_iou_stdev)
        kidney_row += 1

        kidney_sheet.write(kidney_row,0,"mean t1")
        kidney_sheet.write(kidney_row,1,kidney_t1_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_t1_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_t1_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_t1_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev t1")
        kidney_sheet.write(kidney_row,1,kidney_t1_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_t1_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_t1_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_t1_iou_stdev)
        kidney_row += 1

        kidney_sheet.write(kidney_row,0,"mean t2")
        kidney_sheet.write(kidney_row,1,kidney_t2_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_t2_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_t2_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_t2_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev t2")
        kidney_sheet.write(kidney_row,1,kidney_t2_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_t2_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_t2_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_t2_iou_stdev)
        kidney_row += 1

        kidney_sheet.write(kidney_row,0,"mean all kidney img params")
        kidney_sheet.write(kidney_row,1,kidney_all_dist_mm_mean)
        kidney_sheet.write(kidney_row,2,kidney_all_dist_pix_mean)
        kidney_sheet.write(kidney_row,3,kidney_all_dice_mean)
        kidney_sheet.write(kidney_row,4,kidney_all_iou_mean)
        kidney_row += 1
        kidney_sheet.write(kidney_row,0,"stdev all kidney img params")
        kidney_sheet.write(kidney_row,1,kidney_all_dist_mm_stdev)
        kidney_sheet.write(kidney_row,2,kidney_all_dist_pix_stdev)
        kidney_sheet.write(kidney_row,3,kidney_all_dice_stdev)
        kidney_sheet.write(kidney_row,4,kidney_all_iou_stdev)
        kidney_row += 1


   

    if agents >= 2:
        troch_in_dist_pix_mean = statistics.mean(troch_in_dist_pix_list)
        troch_in_dist_mm_mean = statistics.mean(troch_in_dist_mm_list)
        troch_in_dice_mean = statistics.mean(troch_in_dice_list)
        troch_in_iou_mean = statistics.mean(troch_in_iou_list)
        troch_in_dist_pix_stdev = statistics.stdev(troch_in_dist_pix_list)
        troch_in_dist_mm_stdev = statistics.stdev(troch_in_dist_mm_list)
        troch_in_dice_stdev = statistics.stdev(troch_in_dice_list)
        troch_in_iou_stdev = statistics.stdev(troch_in_iou_list)

        troch_opp_dist_pix_mean = statistics.mean(troch_opp_dist_pix_list)
        troch_opp_dist_mm_mean = statistics.mean(troch_opp_dist_mm_list)
        troch_opp_dice_mean = statistics.mean(troch_opp_dice_list)
        troch_opp_iou_mean = statistics.mean(troch_opp_iou_list)
        troch_opp_dist_pix_stdev = statistics.stdev(troch_opp_dist_pix_list)
        troch_opp_dist_mm_stdev = statistics.stdev(troch_opp_dist_mm_list)
        troch_opp_dice_stdev = statistics.stdev(troch_opp_dice_list)
        troch_opp_iou_stdev = statistics.stdev(troch_opp_iou_list)

        troch_F_dist_pix_mean = statistics.mean(troch_F_dist_pix_list)
        troch_F_dist_mm_mean = statistics.mean(troch_F_dist_mm_list)
        troch_F_dice_mean = statistics.mean(troch_F_dice_list)
        troch_F_iou_mean = statistics.mean(troch_F_iou_list)
        troch_F_dist_pix_stdev = statistics.stdev(troch_F_dist_pix_list)
        troch_F_dist_mm_stdev = statistics.stdev(troch_F_dist_mm_list)
        troch_F_dice_stdev = statistics.stdev(troch_F_dice_list)
        troch_F_iou_stdev = statistics.stdev(troch_F_iou_list)

        troch_W_dist_pix_mean = statistics.mean(troch_W_dist_pix_list)
        troch_W_dist_mm_mean = statistics.mean(troch_W_dist_mm_list)
        troch_W_dice_mean = statistics.mean(troch_W_dice_list)
        troch_W_iou_mean = statistics.mean(troch_W_iou_list)
        troch_W_dist_pix_stdev = statistics.stdev(troch_W_dist_pix_list)
        troch_W_dist_mm_stdev = statistics.stdev(troch_W_dist_mm_list)
        troch_W_dice_stdev = statistics.stdev(troch_W_dice_list)
        troch_W_iou_stdev = statistics.stdev(troch_W_iou_list)

        troch_t1_dist_pix_mean = statistics.mean(troch_t1_dist_pix_list)
        troch_t1_dist_mm_mean = statistics.mean(troch_t1_dist_mm_list)
        troch_t1_dice_mean = statistics.mean(troch_t1_dice_list)
        troch_t1_iou_mean = statistics.mean(troch_t1_iou_list)
        troch_t1_dist_pix_stdev = statistics.stdev(troch_t1_dist_pix_list)
        troch_t1_dist_mm_stdev = statistics.stdev(troch_t1_dist_mm_list)
        troch_t1_dice_stdev = statistics.stdev(troch_t1_dice_list)
        troch_t1_iou_stdev = statistics.stdev(troch_t1_iou_list)

        troch_t2_dist_pix_mean = statistics.mean(troch_t2_dist_pix_list)
        troch_t2_dist_mm_mean = statistics.mean(troch_t2_dist_mm_list)
        troch_t2_dice_mean = statistics.mean(troch_t2_dice_list)
        troch_t2_iou_mean = statistics.mean(troch_t2_iou_list)
        troch_t2_dist_pix_stdev = statistics.stdev(troch_t2_dist_pix_list)
        troch_t2_dist_mm_stdev = statistics.stdev(troch_t2_dist_mm_list)
        troch_t2_dice_stdev = statistics.stdev(troch_t2_dice_list)
        troch_t2_iou_stdev = statistics.stdev(troch_t2_iou_list)
        

        troch_all_dist_pix_mean = statistics.mean(troch_all_dist_pix_list)
        troch_all_dist_mm_mean = statistics.mean(troch_all_dist_mm_list)
        troch_all_dice_mean = statistics.mean(troch_all_dice_list)
        troch_all_iou_mean = statistics.mean(troch_all_iou_list)
        troch_all_dist_pix_stdev = statistics.stdev(troch_all_dist_pix_list)
        troch_all_dist_mm_stdev = statistics.stdev(troch_all_dist_mm_list)
        troch_all_dice_stdev = statistics.stdev(troch_all_dice_list)
        troch_all_iou_stdev = statistics.stdev(troch_all_iou_list)

        troch_sheet.write(troch_row,0,"mean in")
        troch_sheet.write(troch_row,1,troch_in_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_in_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_in_dice_mean)
        troch_sheet.write(troch_row,4,troch_in_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev in")
        troch_sheet.write(troch_row,1,troch_in_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_in_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_in_dice_stdev)
        troch_sheet.write(troch_row,4,troch_in_iou_stdev)
        troch_row += 1

        troch_sheet.write(troch_row,0,"mean opp")
        troch_sheet.write(troch_row,1,troch_opp_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_opp_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_opp_dice_mean)
        troch_sheet.write(troch_row,4,troch_opp_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev opp")
        troch_sheet.write(troch_row,1,troch_opp_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_opp_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_opp_dice_stdev)
        troch_sheet.write(troch_row,4,troch_opp_iou_stdev)
        troch_row += 1


        troch_sheet.write(troch_row,0,"mean F")
        troch_sheet.write(troch_row,1,troch_F_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_F_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_F_dice_mean)
        troch_sheet.write(troch_row,4,troch_F_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev F")
        troch_sheet.write(troch_row,1,troch_F_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_F_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_F_dice_stdev)
        troch_sheet.write(troch_row,4,troch_F_iou_stdev)
        troch_row += 1

        troch_sheet.write(troch_row,0,"mean W")
        troch_sheet.write(troch_row,1,troch_W_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_W_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_W_dice_mean)
        troch_sheet.write(troch_row,4,troch_W_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev W")
        troch_sheet.write(troch_row,1,troch_W_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_W_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_W_dice_stdev)
        troch_sheet.write(troch_row,4,troch_W_iou_stdev)
        troch_row += 1

        troch_sheet.write(troch_row,0,"mean t1")
        troch_sheet.write(troch_row,1,troch_t1_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_t1_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_t1_dice_mean)
        troch_sheet.write(troch_row,4,troch_t1_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev t1")
        troch_sheet.write(troch_row,1,troch_t1_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_t1_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_t1_dice_stdev)
        troch_sheet.write(troch_row,4,troch_t1_iou_stdev)
        troch_row += 1

        troch_sheet.write(troch_row,0,"mean t2")
        troch_sheet.write(troch_row,1,troch_t2_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_t2_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_t2_dice_mean)
        troch_sheet.write(troch_row,4,troch_t2_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev t2")
        troch_sheet.write(troch_row,1,troch_t2_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_t2_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_t2_dice_stdev)
        troch_sheet.write(troch_row,4,troch_t2_iou_stdev)
        troch_row += 1

        troch_sheet.write(troch_row,0,"mean all troch img params")
        troch_sheet.write(troch_row,1,troch_all_dist_mm_mean)
        troch_sheet.write(troch_row,2,troch_all_dist_pix_mean)
        troch_sheet.write(troch_row,3,troch_all_dice_mean)
        troch_sheet.write(troch_row,4,troch_all_iou_mean)
        troch_row += 1
        troch_sheet.write(troch_row,0,"stdev all troch img params")
        troch_sheet.write(troch_row,1,troch_all_dist_mm_stdev)
        troch_sheet.write(troch_row,2,troch_all_dist_pix_stdev)
        troch_sheet.write(troch_row,3,troch_all_dice_stdev)
        troch_sheet.write(troch_row,4,troch_all_iou_stdev)
        troch_row += 1





    if agents >= 3:
        heart_in_dist_pix_mean = statistics.mean(heart_in_dist_pix_list)
        heart_in_dist_mm_mean = statistics.mean(heart_in_dist_mm_list)
        heart_in_dice_mean = statistics.mean(heart_in_dice_list)
        heart_in_iou_mean = statistics.mean(heart_in_iou_list)
        heart_in_dist_pix_stdev = statistics.stdev(heart_in_dist_pix_list)
        heart_in_dist_mm_stdev = statistics.stdev(heart_in_dist_mm_list)
        heart_in_dice_stdev = statistics.stdev(heart_in_dice_list)
        heart_in_iou_stdev = statistics.stdev(heart_in_iou_list)

        heart_opp_dist_pix_mean = statistics.mean(heart_opp_dist_pix_list)
        heart_opp_dist_mm_mean = statistics.mean(heart_opp_dist_mm_list)
        heart_opp_dice_mean = statistics.mean(heart_opp_dice_list)
        heart_opp_iou_mean = statistics.mean(heart_opp_iou_list)
        heart_opp_dist_pix_stdev = statistics.stdev(heart_opp_dist_pix_list)
        heart_opp_dist_mm_stdev = statistics.stdev(heart_opp_dist_mm_list)
        heart_opp_dice_stdev = statistics.stdev(heart_opp_dice_list)
        heart_opp_iou_stdev = statistics.stdev(heart_opp_iou_list)

        heart_F_dist_pix_mean = statistics.mean(heart_F_dist_pix_list)
        heart_F_dist_mm_mean = statistics.mean(heart_F_dist_mm_list)
        heart_F_dice_mean = statistics.mean(heart_F_dice_list)
        heart_F_iou_mean = statistics.mean(heart_F_iou_list)
        heart_F_dist_pix_stdev = statistics.stdev(heart_F_dist_pix_list)
        heart_F_dist_mm_stdev = statistics.stdev(heart_F_dist_mm_list)
        heart_F_dice_stdev = statistics.stdev(heart_F_dice_list)
        heart_F_iou_stdev = statistics.stdev(heart_F_iou_list)

        heart_W_dist_pix_mean = statistics.mean(heart_W_dist_pix_list)
        heart_W_dist_mm_mean = statistics.mean(heart_W_dist_mm_list)
        heart_W_dice_mean = statistics.mean(heart_W_dice_list)
        heart_W_iou_mean = statistics.mean(heart_W_iou_list)
        heart_W_dist_pix_stdev = statistics.stdev(heart_W_dist_pix_list)
        heart_W_dist_mm_stdev = statistics.stdev(heart_W_dist_mm_list)
        heart_W_dice_stdev = statistics.stdev(heart_W_dice_list)
        heart_W_iou_stdev = statistics.stdev(heart_W_iou_list)

        heart_t1_dist_pix_mean = statistics.mean(heart_t1_dist_pix_list)
        heart_t1_dist_mm_mean = statistics.mean(heart_t1_dist_mm_list)
        heart_t1_dice_mean = statistics.mean(heart_t1_dice_list)
        heart_t1_iou_mean = statistics.mean(heart_t1_iou_list)
        heart_t1_dist_pix_stdev = statistics.stdev(heart_t1_dist_pix_list)
        heart_t1_dist_mm_stdev = statistics.stdev(heart_t1_dist_mm_list)
        heart_t1_dice_stdev = statistics.stdev(heart_t1_dice_list)
        heart_t1_iou_stdev = statistics.stdev(heart_t1_iou_list)

        heart_t2_dist_pix_mean = statistics.mean(heart_t2_dist_pix_list)
        heart_t2_dist_mm_mean = statistics.mean(heart_t2_dist_mm_list)
        heart_t2_dice_mean = statistics.mean(heart_t2_dice_list)
        heart_t2_iou_mean = statistics.mean(heart_t2_iou_list)
        heart_t2_dist_pix_stdev = statistics.stdev(heart_t2_dist_pix_list)
        heart_t2_dist_mm_stdev = statistics.stdev(heart_t2_dist_mm_list)
        heart_t2_dice_stdev = statistics.stdev(heart_t2_dice_list)
        heart_t2_iou_stdev = statistics.stdev(heart_t2_iou_list)


        heart_all_dist_pix_mean = statistics.mean(heart_all_dist_pix_list)
        heart_all_dist_mm_mean = statistics.mean(heart_all_dist_mm_list)
        heart_all_dice_mean = statistics.mean(heart_all_dice_list)
        heart_all_iou_mean = statistics.mean(heart_all_iou_list)
        heart_all_dist_pix_stdev = statistics.stdev(heart_all_dist_pix_list)
        heart_all_dist_mm_stdev = statistics.stdev(heart_all_dist_mm_list)
        heart_all_dice_stdev = statistics.stdev(heart_all_dice_list)
        heart_all_iou_stdev = statistics.stdev(heart_all_iou_list)

        heart_sheet.write(heart_row,0,"mean in")
        heart_sheet.write(heart_row,1,heart_in_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_in_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_in_dice_mean)
        heart_sheet.write(heart_row,4,heart_in_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev in")
        heart_sheet.write(heart_row,1,heart_in_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_in_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_in_dice_stdev)
        heart_sheet.write(heart_row,4,heart_in_iou_stdev)
        heart_row += 1

        heart_sheet.write(heart_row,0,"mean opp")
        heart_sheet.write(heart_row,1,heart_opp_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_opp_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_opp_dice_mean)
        heart_sheet.write(heart_row,4,heart_opp_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev opp")
        heart_sheet.write(heart_row,1,heart_opp_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_opp_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_opp_dice_stdev)
        heart_sheet.write(heart_row,4,heart_opp_iou_stdev)
        heart_row += 1


        heart_sheet.write(heart_row,0,"mean F")
        heart_sheet.write(heart_row,1,heart_F_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_F_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_F_dice_mean)
        heart_sheet.write(heart_row,4,heart_F_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev F")
        heart_sheet.write(heart_row,1,heart_F_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_F_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_F_dice_stdev)
        heart_sheet.write(heart_row,4,heart_F_iou_stdev)
        heart_row += 1

        heart_sheet.write(heart_row,0,"mean W")
        heart_sheet.write(heart_row,1,heart_W_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_W_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_W_dice_mean)
        heart_sheet.write(heart_row,4,heart_W_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev W")
        heart_sheet.write(heart_row,1,heart_W_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_W_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_W_dice_stdev)
        heart_sheet.write(heart_row,4,heart_W_iou_stdev)
        heart_row += 1

        heart_sheet.write(heart_row,0,"mean t1")
        heart_sheet.write(heart_row,1,heart_t1_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_t1_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_t1_dice_mean)
        heart_sheet.write(heart_row,4,heart_t1_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev t1")
        heart_sheet.write(heart_row,1,heart_t1_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_t1_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_t1_dice_stdev)
        heart_sheet.write(heart_row,4,heart_t1_iou_stdev)
        heart_row += 1

        heart_sheet.write(heart_row,0,"mean t2")
        heart_sheet.write(heart_row,1,heart_t2_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_t2_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_t2_dice_mean)
        heart_sheet.write(heart_row,4,heart_t2_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev t2")
        heart_sheet.write(heart_row,1,heart_t2_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_t2_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_t2_dice_stdev)
        heart_sheet.write(heart_row,4,heart_t2_iou_stdev)
        heart_row += 1

        heart_sheet.write(heart_row,0,"mean all heart img params")
        heart_sheet.write(heart_row,1,heart_all_dist_mm_mean)
        heart_sheet.write(heart_row,2,heart_all_dist_pix_mean)
        heart_sheet.write(heart_row,3,heart_all_dice_mean)
        heart_sheet.write(heart_row,4,heart_all_iou_mean)
        heart_row += 1
        heart_sheet.write(heart_row,0,"stdev all heart img params")
        heart_sheet.write(heart_row,1,heart_all_dist_mm_stdev)
        heart_sheet.write(heart_row,2,heart_all_dist_pix_stdev)
        heart_sheet.write(heart_row,3,heart_all_dice_stdev)
        heart_sheet.write(heart_row,4,heart_all_iou_stdev)
        heart_row += 1




    if agents >= 4:
        knee_in_dist_pix_mean = statistics.mean(knee_in_dist_pix_list)
        knee_in_dist_mm_mean = statistics.mean(knee_in_dist_mm_list)
        knee_in_dice_mean = statistics.mean(knee_in_dice_list)
        knee_in_iou_mean = statistics.mean(knee_in_iou_list)
        knee_in_dist_pix_stdev = statistics.stdev(knee_in_dist_pix_list)
        knee_in_dist_mm_stdev = statistics.stdev(knee_in_dist_mm_list)
        knee_in_dice_stdev = statistics.stdev(knee_in_dice_list)
        knee_in_iou_stdev = statistics.stdev(knee_in_iou_list)

        knee_opp_dist_pix_mean = statistics.mean(knee_opp_dist_pix_list)
        knee_opp_dist_mm_mean = statistics.mean(knee_opp_dist_mm_list)
        knee_opp_dice_mean = statistics.mean(knee_opp_dice_list)
        knee_opp_iou_mean = statistics.mean(knee_opp_iou_list)
        knee_opp_dist_pix_stdev = statistics.stdev(knee_opp_dist_pix_list)
        knee_opp_dist_mm_stdev = statistics.stdev(knee_opp_dist_mm_list)
        knee_opp_dice_stdev = statistics.stdev(knee_opp_dice_list)
        knee_opp_iou_stdev = statistics.stdev(knee_opp_iou_list)

        knee_F_dist_pix_mean = statistics.mean(knee_F_dist_pix_list)
        knee_F_dist_mm_mean = statistics.mean(knee_F_dist_mm_list)
        knee_F_dice_mean = statistics.mean(knee_F_dice_list)
        knee_F_iou_mean = statistics.mean(knee_F_iou_list)
        knee_F_dist_pix_stdev = statistics.stdev(knee_F_dist_pix_list)
        knee_F_dist_mm_stdev = statistics.stdev(knee_F_dist_mm_list)
        knee_F_dice_stdev = statistics.stdev(knee_F_dice_list)
        knee_F_iou_stdev = statistics.stdev(knee_F_iou_list)

        knee_W_dist_pix_mean = statistics.mean(knee_W_dist_pix_list)
        knee_W_dist_mm_mean = statistics.mean(knee_W_dist_mm_list)
        knee_W_dice_mean = statistics.mean(knee_W_dice_list)
        knee_W_iou_mean = statistics.mean(knee_W_iou_list)
        knee_W_dist_pix_stdev = statistics.stdev(knee_W_dist_pix_list)
        knee_W_dist_mm_stdev = statistics.stdev(knee_W_dist_mm_list)
        knee_W_dice_stdev = statistics.stdev(knee_W_dice_list)
        knee_W_iou_stdev = statistics.stdev(knee_W_iou_list)

        knee_t1_dist_pix_mean = statistics.mean(knee_t1_dist_pix_list)
        knee_t1_dist_mm_mean = statistics.mean(knee_t1_dist_mm_list)
        knee_t1_dice_mean = statistics.mean(knee_t1_dice_list)
        knee_t1_iou_mean = statistics.mean(knee_t1_iou_list)
        knee_t1_dist_pix_stdev = statistics.stdev(knee_t1_dist_pix_list)
        knee_t1_dist_mm_stdev = statistics.stdev(knee_t1_dist_mm_list)
        knee_t1_dice_stdev = statistics.stdev(knee_t1_dice_list)
        knee_t1_iou_stdev = statistics.stdev(knee_t1_iou_list)

        knee_t2_dist_pix_mean = statistics.mean(knee_t2_dist_pix_list)
        knee_t2_dist_mm_mean = statistics.mean(knee_t2_dist_mm_list)
        knee_t2_dice_mean = statistics.mean(knee_t2_dice_list)
        knee_t2_iou_mean = statistics.mean(knee_t2_iou_list)
        knee_t2_dist_pix_stdev = statistics.stdev(knee_t2_dist_pix_list)
        knee_t2_dist_mm_stdev = statistics.stdev(knee_t2_dist_mm_list)
        knee_t2_dice_stdev = statistics.stdev(knee_t2_dice_list)
        knee_t2_iou_stdev = statistics.stdev(knee_t2_iou_list)

        knee_all_dist_pix_mean = statistics.mean(knee_all_dist_pix_list)
        knee_all_dist_mm_mean = statistics.mean(knee_all_dist_mm_list)
        knee_all_dice_mean = statistics.mean(knee_all_dice_list)
        knee_all_iou_mean = statistics.mean(knee_all_iou_list)
        knee_all_dist_pix_stdev = statistics.stdev(knee_all_dist_pix_list)
        knee_all_dist_mm_stdev = statistics.stdev(knee_all_dist_mm_list)
        knee_all_dice_stdev = statistics.stdev(knee_all_dice_list)
        knee_all_iou_stdev = statistics.stdev(knee_all_iou_list)

        knee_sheet.write(knee_row,0,"mean in")
        knee_sheet.write(knee_row,1,knee_in_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_in_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_in_dice_mean)
        knee_sheet.write(knee_row,4,knee_in_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev in")
        knee_sheet.write(knee_row,1,knee_in_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_in_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_in_dice_stdev)
        knee_sheet.write(knee_row,4,knee_in_iou_stdev)
        knee_row += 1

        knee_sheet.write(knee_row,0,"mean opp")
        knee_sheet.write(knee_row,1,knee_opp_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_opp_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_opp_dice_mean)
        knee_sheet.write(knee_row,4,knee_opp_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev opp")
        knee_sheet.write(knee_row,1,knee_opp_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_opp_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_opp_dice_stdev)
        knee_sheet.write(knee_row,4,knee_opp_iou_stdev)
        knee_row += 1


        knee_sheet.write(knee_row,0,"mean F")
        knee_sheet.write(knee_row,1,knee_F_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_F_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_F_dice_mean)
        knee_sheet.write(knee_row,4,knee_F_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev F")
        knee_sheet.write(knee_row,1,knee_F_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_F_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_F_dice_stdev)
        knee_sheet.write(knee_row,4,knee_F_iou_stdev)
        knee_row += 1

        knee_sheet.write(knee_row,0,"mean W")
        knee_sheet.write(knee_row,1,knee_W_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_W_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_W_dice_mean)
        knee_sheet.write(knee_row,4,knee_W_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev W")
        knee_sheet.write(knee_row,1,knee_W_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_W_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_W_dice_stdev)
        knee_sheet.write(knee_row,4,knee_W_iou_stdev)
        knee_row += 1

        knee_sheet.write(knee_row,0,"mean t1")
        knee_sheet.write(knee_row,1,knee_t1_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_t1_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_t1_dice_mean)
        knee_sheet.write(knee_row,4,knee_t1_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev t1")
        knee_sheet.write(knee_row,1,knee_t1_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_t1_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_t1_dice_stdev)
        knee_sheet.write(knee_row,4,knee_t1_iou_stdev)
        knee_row += 1

        knee_sheet.write(knee_row,0,"mean t2")
        knee_sheet.write(knee_row,1,knee_t2_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_t2_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_t2_dice_mean)
        knee_sheet.write(knee_row,4,knee_t2_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev t2")
        knee_sheet.write(knee_row,1,knee_t2_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_t2_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_t2_dice_stdev)
        knee_sheet.write(knee_row,4,knee_t2_iou_stdev)
        knee_row += 1

        knee_sheet.write(knee_row,0,"mean all knee img params")
        knee_sheet.write(knee_row,1,knee_all_dist_mm_mean)
        knee_sheet.write(knee_row,2,knee_all_dist_pix_mean)
        knee_sheet.write(knee_row,3,knee_all_dice_mean)
        knee_sheet.write(knee_row,4,knee_all_iou_mean)
        knee_row += 1
        knee_sheet.write(knee_row,0,"stdev all knee img params")
        knee_sheet.write(knee_row,1,knee_all_dist_mm_stdev)
        knee_sheet.write(knee_row,2,knee_all_dist_pix_stdev)
        knee_sheet.write(knee_row,3,knee_all_dice_stdev)
        knee_sheet.write(knee_row,4,knee_all_iou_stdev)
        knee_row += 1



    all_dist_pix_mean = statistics.mean(all_dist_pix_list)
    all_dist_mm_mean = statistics.mean(all_dist_mm_list)
    all_dice_mean = statistics.mean(all_dice_list)
    all_iou_mean = statistics.mean(all_iou_list)
    all_dist_pix_stdev = statistics.stdev(all_dist_pix_list)
    all_dist_mm_stdev = statistics.stdev(all_dist_mm_list)
    all_dice_stdev = statistics.stdev(all_dice_list)
    all_iou_stdev = statistics.stdev(all_iou_list)



    all_sheet.write(all_row,0,"mean all")
    all_sheet.write(all_row,1,all_dist_mm_mean)
    all_sheet.write(all_row,2,all_dist_pix_mean)
    all_sheet.write(all_row,3,all_dice_mean)
    all_sheet.write(all_row,4,all_iou_mean)
    all_row += 1
    all_sheet.write(all_row,0,"stdev all")
    all_sheet.write(all_row,1,all_dist_mm_stdev)
    all_sheet.write(all_row,2,all_dist_pix_stdev)
    all_sheet.write(all_row,3,all_dice_stdev)
    all_sheet.write(all_row,4,all_iou_stdev)
    all_row += 1


    wb.save('MetricsResults_multiagent_3D.xls')



###############################################################################

def eval_with_funcs(predictors, nr_eval, get_player_fn, files_list=None,agents=2,reward_strategy=1):
    """
    Args:
        predictors ([PredictorBase])

    Runs episodes in parallel, returning statistics about the model performance.
    """

    class Worker(StoppableThread, ShareSessionThread):
        def __init__(self, func, queue, distErrorQueue , agents=2):
            super(Worker, self).__init__()
            self.agents=agents
            self._func = func
            self.q = queue
            self.q_dist = distErrorQueue

        def func(self, *args, **kwargs):
            if self.stopped():
                raise RuntimeError("stopped!")
            return self._func(*args, **kwargs)

        def run(self):
            with self.default_sess():
                player = get_player_fn(task=False,
                                       files_list=files_list,agents=self.agents,reward_strategy=reward_strategy)
                while not self.stopped():
                    try:
                        #sum_r, filename, dist, q_values = play_one_episode(player, self.func,agents=self.agents)
                        fname, dist, dist_error_mm_list, dice, iou, sum_r = play_one_episode(player, self.func,agents=self.agents)
                        # print("Score, ", score)
                    except RuntimeError:
                        return
                    for i in range (0,self.agents):
                        self.queue_put_stoppable(self.q, sum_r[i])
                        self.queue_put_stoppable(self.q_dist, dist[i])


    q = queue.Queue()
    q_dist = queue.Queue()

    threads = [Worker(f, q, q_dist,agents=agents) for f in predictors]

    # start all workers
    for k in threads:
        k.start()
        time.sleep(0.1)  # avoid simulator bugs
    stat = StatCounter()
    dist_stat = StatCounter()

    # show progress bar w/ tqdm
    for _ in tqdm(range(nr_eval), **get_tqdm_kwargs()):
        r = q.get()
        stat.feed(r)
        dist = q_dist.get()
        dist_stat.feed(dist)

    logger.info("Waiting for all the workers to finish the last run...")
    for k in threads:
        k.stop()
    for k in threads:
        k.join()
    while q.qsize():
        r = q.get()
        stat.feed(r)

    while q_dist.qsize():
        dist = q_dist.get()
        dist_stat.feed(dist)

    if stat.count > 0:
        return (stat.average, stat.max, dist_stat.average, dist_stat.max)
    return (0, 0, 0, 0)


###############################################################################

def eval_model_multithread(pred, nr_eval, get_player_fn, files_list):
    """
    Args:
        pred (OfflinePredictor): state -> Qvalue

    Evaluate pretrained models, or checkpoints of models during training
    """
    NR_PROC = min(multiprocessing.cpu_count() // 2, 8)
    with pred.sess.as_default():
        mean_score, max_score, mean_dist, max_dist = eval_with_funcs(
            [pred] * NR_PROC, nr_eval, get_player_fn, files_list)
    logger.info("Average Score: {}; Max Score: {}; Average Distance: {}; Max Distance: {}".format(mean_score, max_score, mean_dist, max_dist))

###############################################################################

class Evaluator(Callback):

    def __init__(self, nr_eval, input_names, output_names,
                 get_player_fn, files_list=None,agents=2,reward_strategy=1):
        self.files_list = files_list
        self.eval_episode = nr_eval
        self.input_names = input_names
        self.output_names = output_names
        self.get_player_fn = get_player_fn
        self.agents=agents
        self.reward_strategy=reward_strategy

    def _setup_graph(self):
        NR_PROC = min(multiprocessing.cpu_count() // 2, 20)
        self.pred_funcs = [self.trainer.get_predictor(
            self.input_names, self.output_names)] * NR_PROC

    def _trigger(self):
        """triggered by Trainer"""
        t = time.time()
        mean_score, max_score, mean_dist, max_dist = eval_with_funcs(
            self.pred_funcs, self.eval_episode, self.get_player_fn, self.files_list, agents=self.agents,
            reward_strategy=self.reward_strategy)
        t = time.time() - t
        if t > 10 * 60:  # eval takes too long
            self.eval_episode = int(self.eval_episode * 0.94)

        # log scores
        self.trainer.monitors.put_scalar('mean_score', mean_score)
        self.trainer.monitors.put_scalar('max_score', max_score)
        self.trainer.monitors.put_scalar('mean_distance', mean_dist)
        self.trainer.monitors.put_scalar('max_distance', max_dist)

###############################################################################
