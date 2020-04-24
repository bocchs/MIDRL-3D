#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: medical.py
# Author: Amir Alansary <amiralansary@gmail.com>
# Modified: Athanasios Vlontzos <athanasiosvlontzos@gmail.com>

import csv
import itertools


def warn(*args, **kwargs):
    pass


import warnings

warnings.warn = warn
warnings.simplefilter("ignore", category=PendingDeprecationWarning)
import copy
import os
import sys
import six
import random
import threading
import numpy as np
from tensorpack import logger
from collections import (Counter, defaultdict, deque, namedtuple)

import cv2
import math
import time
from PIL import Image
import subprocess
import shutil

import gym
from gym import spaces

try:
    import pyglet
except ImportError as e:
    reraise(suffix="HINT: you can install pyglet directly via 'pip install pyglet'.")

from tensorpack.utils.utils import get_rng
from tensorpack.utils.stats import StatCounter

from IPython.core.debugger import set_trace
from dataReader import *

_ALE_LOCK = threading.Lock()

Rectangle = namedtuple('Rectangle', ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'])
Rectangle_2d = namedtuple('Rectangle_2d', ['xmin', 'xmax', 'ymin', 'ymax'])

# volume of intersection of two rectangles 
def volume(a, b):  # returns 0 if rectangles don't intersect
    dx = min(a.xmax, b.xmax) - max(a.xmin, b.xmin)
    dy = min(a.ymax, b.ymax) - max(a.ymin, b.ymin)
    dz = min(a.zmax, b.zmax) - max(a.zmin, b.zmin)
    if (dx>=0) and (dy>=0) and (dz >= 0):
        return dx*dy*dz
    else:
        return 0

# area of intersection of two rectangles (2d)
def area(a, b):  # returns 0 if rectangles don't intersect
    dx = min(a.xmax, b.xmax) - max(a.xmin, b.xmin)
    dy = min(a.ymax, b.ymax) - max(a.ymin, b.ymin)
    if (dx>=0) and (dy>=0):
        return dx*dy
    else:
        return 0


# ===================================================================
# =================== 3d medical environment ========================
# ===================================================================

class MedicalPlayer(gym.Env):
    """Class that provides 3D medical image environment.
    This is just an implementation of the classic "agent-environment loop".
    Each time-step, the agent chooses an action, and the environment returns
    an observation and a reward."""

    def __init__(self, directory=None, viz=False, task=False, files_list=None,
                 screen_dims=(27,27,27), history_length=20, multiscale=True,
                 max_num_frames=0, saveGif=False, saveVideo=False ,agents=2,reward_strategy=1):
        """
        :param train_directory: environment or game name
        :param viz: visualization
            set to 0 to disable
            set to +ve number to be the delay between frames to show
            set to a string to be the directory for storing frames
        :param screen_dims: shape of the frame cropped from the image to feed
            it to dqn (d,w,h) - defaults (27,27,27)
        :param nullop_start: start with random number of null ops
        :param location_history_length: consider lost of lives as end of
            episode (useful for training)
        :max_num_frames: maximum numbe0r of frames per episode.
        """
        # self.csvfile = 'DQN_Fetal_agents_2_stategy_1_chkpt275k_RC_CSP.csv'
        self.csvfile = 'test.csv'
        self.reward_strategy = reward_strategy
        # if os.path.exists(self.csvfile): sys.exit('csv file exists')

        # if task!='train':
        #     with open(self.csvfile, 'w') as outcsv:
        #         fields = ["filename", "dist_error"]
        #         writer = csv.writer(outcsv)
        #         writer.writerow(map(lambda x: x, fields))

        x = [0.5, 0.25, 0.75]#0.25,
        y = [0.5, 0.25, 0.75]#0.25,
        z = [0.5, 0.25, 0.75]#0.25,
        self.start_points = []
        for combination in itertools.product(x, y, z):
            if 0.5 in combination: self.start_points.append(combination)
        self.start_points = itertools.cycle(self.start_points)
        self.count_points = 0
        self.total_loc = []
        ######################################################################

        super(MedicalPlayer, self).__init__()
        # number of agents
        self.agents = agents

        # inits stat counters
        self.reset_stat()

        # counter to limit number of steps per episodes
        self.cnt = 0
        # maximum number of frames (steps) per episodes
        self.max_num_frames = max_num_frames
        # stores information: terminal, score, distError
        self.info = None
        # option to save display as gif
        self.saveGif = saveGif
        self.saveVideo = saveVideo
        # training flag
        self.task = task
        # image dimension (2D/3D)
        self.screen_dims = screen_dims
        self.dims = len(self.screen_dims)
        # multi-scale agent
        self.multiscale = multiscale

        # init env dimensions
        if self.dims == 2:
            self.width, self.height = screen_dims
        else:
            self.width, self.height, self.depth = screen_dims

        with _ALE_LOCK:
            self.rng = get_rng(self)
            # visualization setup
            if isinstance(viz, six.string_types):  # check if viz is a string
                assert os.path.isdir(viz), viz
                viz = 0
            if isinstance(viz, int):
                viz = float(viz)
            self.viz = viz
            if self.viz and isinstance(self.viz, float):
                self.viewer = None
                self.gif_buffer = []


        # get action space and minimal action set
        self.action_space = spaces.Discrete(6)  # change number actions here
        self.actions = self.action_space.n
        self.observation_space = spaces.Box(low=0, high=255,
                                            shape=self.screen_dims,
                                            dtype=np.uint8)
        # history buffer for storing last locations to check oscilations
        self._history_length = history_length
        self._loc_history=[]
        self._qvalues_history=[]
        # stat counter to store current score or accumlated reward
        self.current_episode_score=[]
        self.rectangle=[]
        self.target_rectangle = []
        for i in range(0,self.agents):
            self.current_episode_score.append(StatCounter())
            self._loc_history.append([(0,) * self.dims] * self._history_length)
            self._qvalues_history.append([(0,) * self.actions] * self._history_length)
            self.rectangle.append(Rectangle(0, 0, 0, 0, 0, 0)) # initialize rectangle limits from input image coordinates
            self.target_rectangle.append(Rectangle(0, 0, 0, 0, 0, 0))
            # self.rectangle.append(Rectangle_2d(0, 0, 0, 0)) # initialize rectangle limits from input image coordinates
            # self.target_rectangle.append(Rectangle_2d(0, 0, 0, 0))

        # add your data loader here
        if self.task == 'play':
            self.files = filesListCardioMRLandmark(files_list,
                                                  returnLandmarks=False,
                                                  agents=self.agents)
        else:
            self.files = filesListCardioMRLandmark(files_list,
                                                  returnLandmarks=True,
                                                  agents=self.agents)


        # prepare file sampler
        self.filepath = None
        self.sampled_files = self.files.sample_circular()
        # reset buffer, terminal, counters, and init new_random_game
        self._restart_episode()

    def reset(self):
        # with _ALE_LOCK:
        self._restart_episode()
        return self._current_state()

    def _restart_episode(self):
        """
        restart current episoide
        """
        self.terminal = [False] * self.agents
        self.reward = np.zeros((self.agents,))
        self.cnt = 0 # counter to limit number of steps per episodes
        self.num_games.feed(1)
        self._loc_history=[]
        self._qvalues_history=[]
        for i in range(0,self.agents):
            self.current_episode_score[i].reset()

            self._loc_history.append([(0,) * self.dims] * self._history_length)
        # list of q-value lists
            self._qvalues_history.append([(0,) * self.actions] * self._history_length)

        self.new_random_game()

    def new_random_game(self):
        """
        load image,
        set dimensions,
        randomize start point,
        init _screen, qvals,
        calc distance to goal
        """
        self.terminal = [False] * self.agents

        self.viewer = None




        if self.task!='train':
            #######################################################################

            print('\n============== new game ===============\n')

            # sample a new image
            self._image, self._target_loc, self.filepath, self.spacing = next(self.sampled_files)
            scale = next(self.start_points)
            self.count_points += 1
            x_temp = int(scale[0] * self._image[0].dims[0])
            y_temp = int(scale[1] * self._image[0].dims[1])
            z_temp = int(scale[2] * self._image[0].dims[2])
            logger.info('starting point {}-{}-{}'.format(x_temp, y_temp, z_temp))
            #######################################################################
        else:
            self._image, self._target_loc, self.filepath, self.spacing = next(self.sampled_files)
        ###################### calculate distance of all the landmarks ################################
        combi = itertools.combinations(range(self.agents), 2)
        combi = list(combi)
        self.all_distances = np.zeros((self.agents,self.agents))
        for a, b in combi:
            self.all_distances[a, b] = self.calcDistance(self._target_loc[a], self._target_loc[b], self.spacing)
            self.all_distances[b, a] = self.all_distances[a, b]
        #######################################################################

        self.filename=[]
        # # sample a new image
        # self._image, self._target_loc, self.filepath, self.spacing = next(self.sampled_files)
        for i in range(0,self.agents):
            self.filename.append(os.path.basename(self.filepath[i]))
        # multiscale (e.g. start with 3 -> 2 -> 1)
        # scale can be thought of as sampling stride
        if self.multiscale:
            ## brain
            self.action_step = 9
            self.xscale = 3
            self.yscale = 3
            self.zscale = 3
            ## cardiac
            # self.action_step =   6
            # self.xscale = 2
            # self.yscale = 2
            # self.zscale = 2
        else:
            self.action_step = 1
            self.xscale = 1
            self.yscale = 1
            self.zscale = 1
        # image volume size
        self._image_dims = self._image[0].dims

        #######################################################################
        ## select random starting point
        # add padding to avoid start right on the border of the image
        if (self.task == 'train'):
            skip_thickness = ((int)(self._image_dims[0]/5),
                              (int)(self._image_dims[1]/5),
                              (int)(self._image_dims[2]/5))
        else:
            skip_thickness = (int(self._image_dims[0] / 4),
                              int(self._image_dims[1] / 4),
                              int(self._image_dims[2] / 4))

        if self.task == 'train':
            x=[]
            y=[]
            z=[]
            for i in range(0,self.agents):
                x.append(self.rng.randint(0 + skip_thickness[0],
                                 self._image_dims[0] - skip_thickness[0]))
                y.append(self.rng.randint(0 + skip_thickness[1],
                                 self._image_dims[1] - skip_thickness[1]))
                z.append(self.rng.randint(0 + skip_thickness[2],
                                 self._image_dims[2] - skip_thickness[2]))
        else:
            x=[]
            y=[]
            z=[]
            for i in range(0,self.agents):
                x.append(x_temp)
                y.append(y_temp)
                z.append(z_temp)


        #######################################################################

        self._location=[]
        self._start_location=[]
        for i in range(0,self.agents):
            self._location.append((x[i], y[i], z[i]))
            self._start_location.append((x[i], y[i], z[i]))


        self._qvalues = [[0, ] * self.actions]*self.agents
        self._screen = self._current_state() # self.rectanle is updated here

        if self.task == 'play':
            self.cur_dist = [0, ]*self.agents
        else:
            self.cur_dist=[]
            for i in range(0,self.agents):
                self.cur_dist.append( self.calcDistance(self._location[i],
                                              self._target_loc[i],
                                              self.spacing))

    def calcDistance(self, points1, points2, spacing=(1, 1, 1)):
        """ calculate the distance between two points in mm"""
        spacing = np.array(spacing)
        points1 = spacing * np.array(points1)
        points2 = spacing * np.array(points2)
        return np.linalg.norm(points1 - points2)

    def step(self, act, q_values, isOver):
        """The environment's step function returns exactly what we need.
        Args:
          act:
        Returns:
          observation (object):
            an environment-specific object representing your observation of
            the environment. For example, pixel data from a camera, joint angles
            and joint velocities of a robot, or the board state in a board game.
          reward (float):
            amount of reward achieved by the previous action. The scale varies
            between environments, but the goal is always to increase your total
            reward.
          done (boolean):
            whether it's time to reset the environment again. Most (but not all)
            tasks are divided up into well-defined episodes, and done being True
            indicates the episode has terminated. (For example, perhaps the pole
            tipped too far, or you lost your last life.)
          info (dict):
            diagnostic information useful for debugging. It can sometimes be
            useful for learning (for example, it might contain the raw
            probabilities behind the environment's last state change). However,
            official evaluations of your agent are not allowed to use this for
            learning.
        """
        for i in range(0,self.agents):
            if isOver[i] : act[i]=10
        self._qvalues = q_values
        current_loc = self._location
        next_location=copy.deepcopy(current_loc)

        self.terminal = [False] * self.agents
        go_out=[False]*self.agents
        ######################## agent i movement #############################
        for i in range(0,self.agents):
            # UP Z+ -----------------------------------------------------------
            if (act[i] == 0):
                next_location[i] = (current_loc[i][0],
                                 current_loc[i][1],
                                 round(current_loc[i][2] + self.action_step))
                if (next_location[i][2] >= self._image_dims[2]):
                    # print(' trying to go out the image Z+ ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True

            # FORWARD Y+ ---------------------------------------------------------
            if (act[i] == 1):
                next_location[i] = (current_loc[i][0],
                                 round(current_loc[i][1] + self.action_step),
                                 current_loc[i][2])
                if (next_location[i][1] >= self._image_dims[1]):
                    # print(' trying to go out the image Y+ ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True
            # RIGHT X+ -----------------------------------------------------------
            if (act[i] == 2):
                next_location[i] = (round(current_loc[i][0] + self.action_step),
                                 current_loc[i][1],
                                 current_loc[i][2])
                if next_location[i][0] >= self._image_dims[0]:
                    # print(' trying to go out the image X+ ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True
            # LEFT X- -----------------------------------------------------------
            if act[i] == 3:
                next_location[i] = (round(current_loc[i][0] - self.action_step),
                                 current_loc[i][1],
                                 current_loc[i][2])
                if next_location[i][0] <= 0:
                    # print(' trying to go out the image X- ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True
            # BACKWARD Y- ---------------------------------------------------------
            if act[i] == 4:
                next_location[i] = (current_loc[i][0],
                                 round(current_loc[i][1] - self.action_step),
                                 current_loc[i][2])
                if next_location[i][1] <= 0:
                    # print(' trying to go out the image Y- ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True
            # DOWN Z- -----------------------------------------------------------
            if act[i] == 5:
                next_location[i] = (current_loc[i][0],
                                 current_loc[i][1],
                                 round(current_loc[i][2] - self.action_step))
                if next_location[i][2] <= 0:
                    # print(' trying to go out the image Z- ',)
                    next_location[i] = current_loc[i]
                    go_out[i] = True
            # -----------------------------------------------------------------

        #######################################################################

        # punish -1 reward if the agent tries to go out
        if (self.task!='play'):
            for i in range(0,self.agents):
                if go_out[i]:
                    self.reward[i]= -1
                else:
                    # if self.task=='train' or self.task=='eval':
                    if self.reward_strategy == 1:
                        self.reward[i] = self._calc_reward(current_loc[i], next_location[i], agent=i)
                    elif self.reward_strategy == 2:
                        self.reward[i] = self._calc_reward_geometric(current_loc[i], next_location[i], agent=i)
                    elif self.reward_strategy == 3:
                        self.reward[i] = self._distance_to_other_agents(current_loc, next_location, agent=i)
                    elif self.reward_strategy == 4:
                        self.reward[i] = self._distance_to_other_agents_and_line(current_loc, next_location, agent=i)
                    elif self.reward_strategy == 5:
                        self.reward[i] = self._distance_to_other_agents_and_line_no_point(current_loc, next_location, agent=i)
                    elif self.reward_strategy == 6:
                        self.reward[i] =  self._calc_reward_geometric_generalized(current_loc[i], next_location[i], agent=i)
                    # else:
                    #     self.reward[i]= self._calc_reward(current_loc[i], next_location[i],agent=i)

        # update screen, reward ,location, terminal
        self._location = next_location
        self._screen = self._current_state()

        # terminate if the distance is less than 1 during trainig
        if (self.task == 'train'):
            for i in range(0,self.agents):
                if self.cur_dist[i]<=1:
                    self.terminal[i]=True
                    self.num_success[i].feed(1)

        # terminate if maximum number of steps is reached
        self.cnt += 1
        if self.cnt >= self.max_num_frames:
            for i in range(0,self.agents):
                self.terminal[i] = True

        # update history buffer with new location and qvalues
        if (self.task != 'play'):
            for i in range(0,self.agents):
                self.cur_dist[i] = self.calcDistance(self._location[i],
                                                         self._target_loc[i],
                                                         self.spacing)



        self._update_history()

        # check if agent oscillates
        if self._oscillate:
            self._location = self.getBestLocation()
            # self._location=[item for sublist in temp for item in sublist]
            self._screen = self._current_state()

            if (self.task != 'play'):
                for i in range(0, self.agents):
                    self.cur_dist[i] = self.calcDistance(self._location[i],
                                                             self._target_loc[i],
                                                             self.spacing)


            # multi-scale steps
            if self.multiscale:
                if self.xscale > 1:
                    self.xscale -= 1
                    self.yscale -= 1
                    self.zscale -= 1
                    self.action_step = int(self.action_step / 3)
                    self._clear_history()
                # terminate if scale is less than 1
                else:

                    for i in range(0,self.agents):
                        self.terminal[i] = True
                        if self.cur_dist[i] <= 1 :
                            self.num_success[i].feed(1)

            else:

                for i in range(0, self.agents):
                    self.terminal[i] = True
                    if self.cur_dist[i] <= 1:
                        self.num_success[i].feed(1)
        # render screen if viz is on
        with _ALE_LOCK:
            if self.viz:
                if isinstance(self.viz, float):
                    # use if statement if don't want to save entire episode gif (runs faster)
                    if all(self.terminal): 
                        self.display() # self.target_rectangle updated here, needed to get dist and overlap


        distance_error = self.cur_dist
        for i in range(0,self.agents):
            self.current_episode_score[i].feed(self.reward[i])


        info = {}
        self.dice = np.zeros((self.agents,))
        self.iou = np.zeros((self.agents,))

        curr_space = (1.5625, 1.5625, 5) # for Dixon and T1
        if "_t2_" in self.filepath:
            curr_space = (1.9531, 1.9531, 5)

        curr_space_2d = (1.5625, 1.5625) # for Dixon and T1
        if "_t2_" in self.filepath:
            curr_space_2d = (1.9531, 1.9531)

        self.iou_ra = self.agents*[0]
        self.dice_ra = self.agents*[0]

        for i in range(0,self.agents):
            info['score_{}'.format(i)]=self.current_episode_score[i].sum
            info['gameOver_{}'.format(i)]=self.terminal[i]
            info['filename_{}'.format(i)]=self.filename[i]
            # distance in 3D
            dist_error_pixels = self.calcDistance(self._location[i], self._target_loc[i], (1,1,1))
            dist_error_mm = self.calcDistance(self._location[i], self._target_loc[i], curr_space)
            # print("pix error = " + str(dist_error_pixels))
            # print("mm error = " + str(dist_error_mm))
            info['distErrorPix_{}'.format(i)]= dist_error_pixels
            info['distErrorMM_{}'.format(i)] = dist_error_mm
            # overlap in 3D 
            intersection = volume(self.rectangle[i], self.target_rectangle[i])
            volume_rectangle = volume(self.rectangle[i], self.rectangle[i])
            volume_target_rectangle = volume(self.target_rectangle[i], self.target_rectangle[i])
            union = volume_rectangle + volume_target_rectangle - intersection
            dice =  2 * intersection / (volume_rectangle + volume_target_rectangle)
            IoU = intersection / union
            self.dice[i] = dice
            self.iou[i] = IoU

        info['filename'] = self.filename


        return self._current_state(), self.reward, self.terminal, info

    def getBestLocation(self):
        ''' get best location with best qvalue from last for locations
        stored in history
        '''
        best_location = []
        for i in range(0,self.agents):
            last_qvalues_history=self._qvalues_history[i][-4:]
            last_loc_history= self._loc_history[i][-4:]
            best_qvalues=np.max(last_qvalues_history, axis=1)
            best_idx=best_qvalues.argmin()
            best_location.append(last_loc_history[best_idx])
        #
        # last_qvalues_history=[]
        # last_loc_history=[]
        # best_qvalues=[]
        # best_idx=[]
        #
        # for i in range(0,self.agents):
        #     last_qvalues_history.append(self._qvalues_history[i][-4:])
        #     last_loc_history.append( self._loc_history[i][-4:])
        #     best_qvalues.append(np.max(last_qvalues_history[i], axis=1))
        #     best_idx.append(best_qvalues[i].argmin())
        #     best_location.append(last_loc_history[best_idx[i]])

        return best_location

    def _clear_history(self):
        ''' clear history buffer with current state
        '''
        self._loc_history=[]
        self._qvalues_history=[]
        for i in range(0,self.agents):
            self._loc_history.append([(0,) * self.dims] * self._history_length)
            self._qvalues_history.append([(0,) * self.actions] * self._history_length)



    def _update_history(self):
        ''' update history buffer with current state
        '''
        # update location history
        for i in range(0,self.agents):
            self._loc_history[i][:-1]=self._loc_history[i][1:]
            self._loc_history[i][-1] = self._location[i]

        # update q-value history
            self._qvalues_history[i][:-1]=self._qvalues_history[i][1:]
            self._qvalues_history[i][-1]=np.ravel(self._qvalues[i])

    def _current_state(self):
        """
        crop image data around current location to update what network sees.
        update rectangle

        :return: new state
        """
        # initialize screen with zeros - all background

        screen = np.zeros((self.agents,self.screen_dims[0],self.screen_dims[1],self.screen_dims[2])).astype(self._image[0].data.dtype)

        for i in range(0,self.agents):
            # screen uses coordinate system relative to origin (0, 0, 0)
            screen_xmin, screen_ymin, screen_zmin = 0, 0, 0
            screen_xmax, screen_ymax, screen_zmax = self.screen_dims

        # extract boundary locations using coordinate system relative to "global" image
        # width, height, depth in terms of screen coord system

            if self.xscale % 2:
                xmin = self._location[i][0] - int(self.width * self.xscale / 2) - 1
                xmax = self._location[i][0] + int(self.width * self.xscale / 2)
                ymin = self._location[i][1] - int(self.height * self.yscale / 2) - 1
                ymax = self._location[i][1] + int(self.height * self.yscale / 2)
                zmin = self._location[i][2] - int(self.depth * self.zscale / 2) - 1
                zmax = self._location[i][2] + int(self.depth * self.zscale / 2)
            else:
                xmin = self._location[i][0] - round(self.width * self.xscale / 2)
                xmax = self._location[i][0] + round(self.width * self.xscale / 2)
                ymin = self._location[i][1] - round(self.height * self.yscale / 2)
                ymax = self._location[i][1] + round(self.height * self.yscale / 2)
                zmin = self._location[i][2] - round(self.depth * self.zscale / 2)
                zmax = self._location[i][2] + round(self.depth * self.zscale / 2)

        ###########################################################

            # check if they violate image boundary and fix it
            if xmin < 0:
                xmin = 0
                screen_xmin = screen_xmax - len(np.arange(xmin, xmax, self.xscale))
            if ymin < 0:
                ymin = 0
                screen_ymin = screen_ymax - len(np.arange(ymin, ymax, self.yscale))
            if zmin < 0:
                zmin = 0
                screen_zmin = screen_zmax - len(np.arange(zmin, zmax, self.zscale))
            if xmax > self._image_dims[0]:
                xmax = self._image_dims[0]
                screen_xmax = screen_xmin + len(np.arange(xmin,xmax,self.xscale))
            if ymax>self._image_dims[1]:
                ymax = self._image_dims[1]
                screen_ymax = screen_ymin + len(np.arange(ymin,ymax,self.yscale))
            if zmax>self._image_dims[2]:
                zmax = self._image_dims[2]
                screen_zmax = screen_zmin + len(np.arange(zmin,zmax,self.zscale))

        # crop image data to update what network sees
        # image coordinate system becomes screen coordinates
        # scale can be thought of as a stride
            screen[i,screen_xmin:screen_xmax, screen_ymin:screen_ymax, screen_zmin:screen_zmax] = self._image[i].data[xmin:xmax:self.xscale, ymin:ymax:self.yscale, zmin:zmax:self.zscale]

        ###########################################################
        # update rectangle limits from input image coordinates
        # this is what the network sees
            self.rectangle[i] = Rectangle(xmin, xmax,
                                          ymin, ymax,
                                          zmin, zmax)
            # self.rectangle[i] = Rectangle_2d(xmin, xmax,
            #                               ymin, ymax)


        return screen

    def get_plane(self, z=0,agent=0):
        return self._image[agent].data[:, :, z]

    def _calc_reward(self, current_loc, next_loc,agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """


        curr_dist = self.calcDistance(current_loc, self._target_loc[agent],
                                  self.spacing)
        next_dist = self.calcDistance(next_loc, self._target_loc[agent],
                                  self.spacing)
        dist=curr_dist - next_dist


        return dist


    def _calc_reward_geometric(self, current_loc, next_loc,agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """
        curr_dist_line=np.linalg.norm(np.cross(self._target_loc[0] - current_loc,
                                                             self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(
                            self._target_loc[0] - self._target_loc[1])
        next_dist_line = np.linalg.norm(np.cross(self._target_loc[0] - next_loc,
                                                 self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(
            self._target_loc[0] - self._target_loc[1])

        curr_dist = self.calcDistance(current_loc, self._target_loc[agent],
                                  self.spacing)
        next_dist = self.calcDistance(next_loc, self._target_loc[agent],
                                  self.spacing)
        dist=curr_dist - next_dist
        dist_line = curr_dist_line - next_dist_line

        tot_dist = dist + dist_line
        return tot_dist

    def _calc_reward_geometric_generalized(self, current_loc, next_loc,agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """
        curr_dist_line=[]
        next_dist_line=[]
        for i in range(0,self.agents):
            if i != agent:

                curr_dist_line.append(np.linalg.norm(np.cross(self._target_loc[agent] - current_loc, self._target_loc[agent] - self._target_loc[i])) / np.linalg.norm(self._target_loc[agent] - self._target_loc[i]))
                next_dist_line.append(np.linalg.norm(np.cross(self._target_loc[agent] - next_loc, self._target_loc[agent] - self._target_loc[i])) / np.linalg.norm(
                    self._target_loc[agent] - self._target_loc[i]))

        curr_dist_line = np.mean(curr_dist_line)
        next_dist_line = np.mean(next_dist_line)

        curr_dist = self.calcDistance(current_loc, self._target_loc[agent],
                                  self.spacing)
        next_dist = self.calcDistance(next_loc, self._target_loc[agent],
                                  self.spacing)
        dist=curr_dist - next_dist
        dist_line = curr_dist_line - next_dist_line
        tot_dist = dist + dist_line
        return tot_dist

    def _distance_to_other_agents(self, current_locs, next_locs,agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """
        rel_improv=[]
        for i in range(0,self.agents):
            if agent != i:
                current_loc_distance = self.calcDistance(current_locs[agent],current_locs[i],self.spacing)
                next_loc_distance = self.calcDistance(next_locs[agent],next_locs[i],self.spacing)
                current_distance_target_loc = current_loc_distance - self.all_distances[agent,i]
                next_distance_target_loc = next_loc_distance - self.all_distances[agent,i]
                rel_improv.append(np.abs(current_distance_target_loc) - np.abs(next_distance_target_loc))


        rel_improv = np.mean(rel_improv)

        curr_dist = self.calcDistance(current_locs[agent], self._target_loc[agent],
                                  self.spacing)
        next_dist = self.calcDistance(next_locs[agent], self._target_loc[agent],
                                  self.spacing)
        dist=curr_dist - next_dist

        tot_dist = dist  + rel_improv
        return tot_dist


    def _distance_to_other_agents_and_line(self, current_locs, next_locs,agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """
        rel_improv=[]
        for i in range(0,self.agents):
            if agent != i:
                current_loc_distance = self.calcDistance(current_locs[agent],current_locs[i],self.spacing)
                next_loc_distance = self.calcDistance(next_locs[agent],next_locs[i],self.spacing)
                current_distance_target_loc = current_loc_distance - self.all_distances[agent,i]
                next_distance_target_loc = next_loc_distance - self.all_distances[agent,i]
                rel_improv.append(np.abs(current_distance_target_loc) - np.abs(next_distance_target_loc))


        rel_improv = np.mean(rel_improv)

        curr_dist_line=np.linalg.norm(np.cross(self._target_loc[0] - current_locs[agent], self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(self._target_loc[0] - self._target_loc[1])
        next_dist_line = np.linalg.norm(np.cross(self._target_loc[0] - next_locs[agent], self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(
            self._target_loc[0] - self._target_loc[1])
        curr_dist = self.calcDistance(current_locs[agent], self._target_loc[agent], self.spacing)
        next_dist = self.calcDistance(next_locs[agent], self._target_loc[agent], self.spacing)
        dist=curr_dist - next_dist
        dist_line = curr_dist_line - next_dist_line
        tot_dist = dist  + dist_line + rel_improv
        return tot_dist

    def _distance_to_other_agents_and_line_no_point(self, current_locs, next_locs, agent):
        """ Calculate the new reward based on the decrease in euclidean distance to the target location
        """
        rel_improv = []
        for i in range(0, self.agents):
            if agent != i:
                current_loc_distance = self.calcDistance(current_locs[agent], current_locs[i], self.spacing)
                next_loc_distance = self.calcDistance(next_locs[agent], next_locs[i], self.spacing)
                current_distance_target_loc = current_loc_distance - self.all_distances[agent, i]
                next_distance_target_loc = next_loc_distance - self.all_distances[agent, i]
                rel_improv.append(np.abs(current_distance_target_loc) - np.abs(next_distance_target_loc))

        rel_improv = np.mean(rel_improv)

        curr_dist_line = np.linalg.norm(np.cross(self._target_loc[0] - current_locs[agent], self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(
            self._target_loc[0] - self._target_loc[1])
        next_dist_line = np.linalg.norm(np.cross(self._target_loc[0] - next_locs[agent], self._target_loc[0] - self._target_loc[1])) / np.linalg.norm(
            self._target_loc[0] - self._target_loc[1])

        dist_line = curr_dist_line - next_dist_line
        tot_dist = dist_line + rel_improv
        return tot_dist


    @property
    def _oscillate(self):
        """ Return True if the agent is stuck and oscillating
        """
        counter=[]
        freq=[]
        for i in range(0,self.agents):
            counter.append(Counter(self._loc_history[i]))
            freq.append(counter[i].most_common())

            if freq[i][0][0] == (0, 0, 0):
                if (freq[i][1][1] > 3):
                    return True
                else:
                    return False
            elif (freq[i][0][1] > 3):
                return True


    def get_action_meanings(self):
        """ return array of integers for actions"""
        ACTION_MEANING = {
            1: "UP",  # MOVE Z+
            2: "FORWARD",  # MOVE Y+
            3: "RIGHT",  # MOVE X+
            4: "LEFT",  # MOVE X-
            5: "BACKWARD",  # MOVE Y-
            6: "DOWN",  # MOVE Z-
        }
        return [ACTION_MEANING[i] for i in self.actions]


    @property
    def getScreenDims(self):
        """
        return screen dimensions
        """
        return (self.width, self.height, self.depth)

    def lives(self):
        return None

    def reset_stat(self):
        """ Reset all statistics counter"""
        self.stats = defaultdict(list)
        self.num_games = StatCounter()
        self.num_success = [StatCounter()]*int(self.agents)


    def display(self, return_rgb_array=False):
        planes = np.transpose(self.get_plane(self._location[0][2], agent=0))
        shape = np.shape(planes)

        shifts_x = [0]
        shifts_y = [0]
        target_points = []
        current_points = []

        
        for i in range(0,self.agents):
            new_location = (self._location[i][0], shape[0] - self._location[i][1], self._location[i][2])
            new_target_loc = (self._target_loc[i][0], shape[0] - self._target_loc[i][1], self._target_loc[i][2])
            current_points.append(new_location)
            target_points.append(new_target_loc)
            # get current plane
            current_plane = np.transpose(self.get_plane(current_points[i][2], agent=i))

            if i !=0:
                # get image in z-axis
                planes = np.hstack((planes, current_plane))
                # get shifts in x and y - results from appending planes
                # shift only in the direction of concat axis
                # shifts_x.append(0)
                # shifts_x.append(np.shape(current_plane)[1])
                shifts_x.append(current_plane.shape[1] + shifts_x[i-1])
                shifts_y.append(0)
                # shifts_y.append(np.shape(current_plane)[1])


        # rescale image
        # INTER_NEAREST, INTER_LINEAR, INTER_AREA, INTER_CUBIC, INTER_LANCZOS4
        scale_y = 1
        scale_x = 1
        img = cv2.resize(
                planes,
                (int(scale_y*planes.shape[1]),int(scale_x*planes.shape[0])),
                interpolation=cv2.INTER_LINEAR
                )

        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        # skip if there is a viewer open
        if (not self.viewer) and self.viz:
            from viewer import SimpleImageViewer
            self.viewer = SimpleImageViewer(arr=img,
                                            scale_y=1,
                                            scale_x=1,
                                            filepath=self.filename[i]+str(i))
            self.gif_buffer = []
        # display image
        self.viewer.draw_image(img)

        for i in range(0,self.agents):
            # get landmarks - correct location if image is flipped and tranposed
            current_point = (shape[0] - current_points[i][1] + shifts_y[i],
                             current_points[i][0] + shifts_x[i],
                             current_points[i][2])
            target_point = (shape[0] - target_points[i][1] + shifts_y[i],
                            target_points[i][0] + shifts_x[i],
                            target_points[i][2])



            # draw current point
            """
            self.viewer.draw_circle(radius=scale_x * 1,
                                    pos_y=scale_y * current_point[1],
                                    pos_x=scale_x * current_point[0],
                                    color=(0.0, 0.0, 1.0, 1.0))
            """
            # draw a box around the agent - what the network sees ROI
            # - correct location if image is flipped
            self.viewer.draw_rect(
                    # scale_y*(shape[0] - self.rectangle[i].ymin + shifts_y[i]),
                    # scale_x*(self.rectangle[i].xmin + shifts_x[i]),
                    # scale_y*(shape[0] - self.rectangle[i].ymax + shifts_y[i]),
                    # scale_x*(self.rectangle[i].xmax + shifts_x[i])),

                    scale_y*(self.rectangle[i].ymin + shifts_y[i]),
                    scale_x*(self.rectangle[i].xmin + shifts_x[i]),
                    scale_y*(self.rectangle[i].ymax + shifts_y[i]),
                    scale_x*(self.rectangle[i].xmax + shifts_x[i])),

            """
            self.viewer.display_text('Agent ' + str(i),
                                     color=(204, 204, 0, 255),
                    x=scale_y*(shape[0]-self.rectangle[i].ymin+shifts_y[i]),
                    y=scale_x*(self.rectangle[i].xmin+shifts_x[i]))
            text = 'Spacing ' + str(self.xscale)
            self.viewer.display_text(text, color = (204,204,0,255),
                                     x=8,
                                     y=8)
                                     #self._image_dims[1]-(int)(0.2*self._image_dims[1])-5)
            """

            # -----------------------------------------------------------------
            if (self.task != 'play'):
                # draw a transparent circle around target point with variable radius
                # based on the difference z-direction
                diff_z = scale_x * abs(current_point[2]-target_point[2])
                """
                self.viewer.draw_circle(radius = diff_z,
                                        pos_x = scale_x*target_point[0],
                                        pos_y = scale_y*target_point[1],
                                        color = (1.0,0.0,0.0,0.2))
                # draw target point
                self.viewer.draw_circle(radius = scale_x * 1,
                                        pos_x = scale_x*target_point[0],
                                        pos_y = scale_y*target_point[1],
                                        color = (1.0,0.0,0.0,1.0))
                # display info
                color = (0,204,0,255) if self.reward[i]>0 else (204,0,0,255)
                text = 'Error - ' + 'Agent ' + str(i) + ' - ' + str(round(self.cur_dist[i],3)) + 'mm'
                self.viewer.display_text(text, color=color,
                                x=scale_y*(int(1.0*shape[0])-15 +shifts_y[i]),
                                y=scale_x*(8+shifts_x[i]))
                """

                if self.xscale % 2:
                    targ_xmin = self._target_loc[i][0] - int(self.width * self.xscale / 2) - 1
                    targ_xmax = self._target_loc[i][0] + int(self.width * self.xscale / 2)
                    targ_ymin = self._target_loc[i][1] - int(self.height * self.yscale / 2) - 1
                    targ_ymax = self._target_loc[i][1] + int(self.height * self.yscale / 2)
                    targ_zmin = self._target_loc[i][2] - int(self.depth * self.zscale / 2) - 1
                    targ_zmax = self._target_loc[i][2] + int(self.depth * self.zscale / 2)
                else:
                    targ_xmin = self._target_loc[i][0] - round(self.width * self.xscale / 2)
                    targ_xmax = self._target_loc[i][0] + round(self.width * self.xscale / 2)
                    targ_ymin = self._target_loc[i][1] - round(self.height * self.yscale / 2)
                    targ_ymax = self._target_loc[i][1] + round(self.height * self.yscale / 2)
                    targ_zmin = self._target_loc[i][2] - round(self.depth * self.zscale / 2)
                    targ_zmax = self._target_loc[i][2] + round(self.depth * self.zscale / 2)


                self.target_rectangle[i] = Rectangle(targ_xmin,targ_xmax,targ_ymin,targ_ymax,targ_zmin,targ_zmax)
                # self.target_rectangle[i] = Rectangle_2d(targ_xmin,targ_xmax,targ_ymin,targ_ymax)
                self.viewer.draw_rect(scale_y*self.target_rectangle[i].ymin + shifts_y[i],
                                      scale_x*self.target_rectangle[i].xmin + shifts_x[i],
                                      scale_y*self.target_rectangle[i].ymax + shifts_y[i],
                                      scale_x*self.target_rectangle[i].xmax + shifts_x[i], 
                                      target=True)

        # -----------------------------------------------------------------

        # render and wait (viz) time between frames

        self.viewer.render()

        # time.sleep(self.viz)
        # save gif
        if self.saveGif:

            image_data = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
            data = image_data.get_data('RGB', image_data.width * 3)
            arr = np.array(bytearray(data)).astype('uint8')
            arr = np.flip(np.reshape(arr, (image_data.height, image_data.width, -1)), 0)
            im = Image.fromarray(arr)
            self.gif_buffer.append(im) 

            if all(self.terminal):
                gifname = self.filename[0].split('.')[0] + '_{}.gif'.format(i)
                gifname = "agent_images/" + gifname
                gifname_terminal = self.filename[0].split('.')[0] + '_{}_terminal.gif'.format(i)
                gifname_terminal = "agent_images/" + gifname_terminal
                print(gifname_terminal)
                self.viewer.saveGif(gifname, arr=self.gif_buffer,
                                    duration=self.viz) ###### ENABLE THIS TO SAVE ENTIRE GIF
                self.viewer.saveGif(gifname_terminal, arr=[im],
                                    duration=self.viz)
        if self.saveVideo:
            dirname = 'tmp_video_cardiac'
            if self.cnt <= 1:
                if os.path.isdir(dirname):
                    logger.warn("""Log directory {} exists! Use 'd' to delete it. """.format(dirname))
                    act = input("select action: d (delete) / q (quit): ").lower().strip()
                    if act == 'd':
                        shutil.rmtree(dirname, ignore_errors=True)
                    else:
                        raise OSError("Directory {} exits!".format(dirname))
                os.mkdir(dirname)

            frame = dirname + '/' + '%04d' % self.cnt + '.png'
            pyglet.image.get_buffer_manager().get_color_buffer().save(frame)
            if all(self.terminal):
                resolution = str(3 * self.viewer.img_width) + 'x' + str(3 * self.viewer.img_height)
                save_cmd = ['ffmpeg', '-f', 'image2', '-framerate', '30',
                            '-pattern_type', 'sequence', '-start_number', '0', '-r',
                            '6', '-i', dirname + '/%04d.png', '-s', resolution,
                            '-vcodec', 'libx264', '-b:v', '2567k', self.filename[0] + '_{}_agents.mp4'.format(i+1)]
                subprocess.check_output(save_cmd)
                shutil.rmtree(dirname, ignore_errors=True)


# =============================================================================
# ================================ FrameStack =================================
# =============================================================================
class FrameStack(gym.Wrapper):
    """used when not training. wrapper for Medical Env"""
    def __init__(self, env, k,agents=2):
        """Buffer observations and stack across channels (last axis)."""
        gym.Wrapper.__init__(self, env)
        self.agents=agents
        self.k = k  # history length
        # self.frames=[]
        # for i in range(0,self.agents):
        self.frames=deque([], maxlen=k)
        shp = env.observation_space.shape
        self._base_dim = len(shp)
        new_shape = shp + (k,)
        self.observation_space = spaces.Box(low=0, high=255, shape=new_shape,
                                            dtype=np.uint8)

    def reset(self):
        """Clear buffer and re-fill by duplicating the first observation."""
        ob = self.env.reset()
        ob=tuple(ob)
        # for i in range(0, self.agents):
        for _ in range(self.k - 1):
            self.frames.append(np.zeros_like(ob))
        self.frames.append(ob)
        return self._observation()

    def step(self, act, q_values,isOver):
        for i in range(0,self.agents):
            if isOver[i]: act[i]=15
        current_st, reward, terminal, info = self.env.step(act, q_values, isOver)
        # for i in range(0,self.agents):
        current_st=tuple(current_st)
        self.frames.append(current_st)
        return self._observation(),reward, terminal, info

    def _observation(self):
        assert len(self.frames) == self.k
        return np.stack(self.frames, axis=-1)



# =============================================================================
# ================================== notes ====================================
# =============================================================================
"""

## Notes from landmark detection Siemens paper
# states  -> ROI - center current pos - size (2D 60x60) (3D 26x26x26)
# actions -> move (up, down, left, right)
# rewards -> delta(d) relative distance change after executing a move (action)

# re-sample -> isotropic (2D 2mm) (3D 1mm)

# gamma = 0.9 , replay memory size P = 100000 , learning rate = 0.00025
# net : 3 conv+pool - 3 FC+dropout (3D kernels for 3d data)

# navigate till oscillation happen (terminate when infinite loop)

# location is a high-confidence landmark -> if the expected reward from this location is max(q*(s_target,a))<1 the agent is closer than one pixel

# object is not in the image: oscillation occurs at points where max(q)>4


## Other Notes:

    DeepMind's original DQN paper
        used frame skipping (for fast playing/learning) and
        applied pixel-wise max to consecutive frames (to handle flickering).

    so an input to the neural network is consisted of four frame;
        [max(T-1, T), max(T+3, T+4), max(T+7, T+8), max(T+11, T+12)]

    ALE provides mechanism for frame skipping (combined with adjustable random action repeat) and color averaging over skipped frames. This is also used in simple_dqn's ALEEnvironment

    Gym's Atari Environment has built-in stochastic frame skipping common to all games. So the frames returned from environment are not consecutive.

    The reason behind Gym's stochastic frame skipping is, as mentioned above, to make environment stochastic. (I guess without this, the game will be completely deterministic?)
    cf. in original DQN and simple_dqn same randomness is achieved by having agent performs random number of dummy actions at the beginning of each episode.

    I think if you want to reproduce the behavior of the original DQN paper, the easiest will be disabling frame skip and color averaging in ALEEnvironment then construct the mechanism on agent side.


"""
