#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ##
# @brief    [Pipette Machine] Pipette Machine Class using Swift Pro + Linear Actuator in Autonomous Laboratory
# @author   Hyuk Jun Yoo (yoohj9475@kist.re.kr)   
# TEST 2021-09-24
# TEST 2022-03-24

from asyncio.windows_utils import pipe
from statistics import mode
import numpy as np
import time
import serial
import os, sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # get import path : logger.py
from Log.Logging_Class import NodeLogger
import functools
from Safety_Protocol.detect_DenseSSD import detection
from Pipette_Machine.uarm.wrapper.swift_api import SwiftAPI
from Computer_Vision.CaptureClass import CaptureClass


def grid_generator(top_left, top_right, bottom_left, bottom_right, num_of_columns=6, num_of_rows=8, index_increment=0):
    # casting parameters
    top_left = dict(top_left)
    top_right = dict(top_right)
    bottom_left = dict(bottom_left)
    bottom_right = dict(bottom_right)

    # init variables
    first_row_x = np.linspace(top_left['x'], top_right['x'], num_of_columns)
    first_row_y = np.linspace(top_left['y'], top_right['y'], num_of_columns)
    first_row_z = np.linspace(top_left['z'], top_right['z'], num_of_columns)
    last_row_x = np.linspace(bottom_left['x'], bottom_right['x'], num_of_columns)
    last_row_y = np.linspace(bottom_left['y'], bottom_right['y'], num_of_columns)
    last_row_z = np.linspace(bottom_left['z'], bottom_right['z'], num_of_columns)

    coordinates_dict = {}

    # iterate and build columns
    for i in range(num_of_columns):
        column_x = np.linspace(first_row_x[i], last_row_x[i], num_of_rows)
        column_y = np.linspace(first_row_y[i], last_row_y[i], num_of_rows)
        column_z = np.linspace(first_row_z[i], last_row_z[i], num_of_rows)
        column_x, column_y, column_z = list(column_x), list(column_y), list(column_z)
        char = 'A'
        for coord in (zip(column_x, column_y, column_z)):
            coordinates_dict[str(char) + str((i + 1) + index_increment)] = {'x': coord[0], 'y': coord[1], 'z': coord[2]}
            char = chr(ord(char) + 1)

    # find the center of the grid
    center_points_x = []
    center_points_y = []
    center_points_z = []
    center_rows_indices = [chr(ord('A') + (num_of_rows + index_increment) // 2)]
    if (num_of_rows + index_increment) % 2 == 0:
        center_rows_indices.append(chr(ord('A') - 1 + (num_of_rows + index_increment) // 2))
    center_columns_indices = [(num_of_rows + index_increment) // 2 + 1]
    if (num_of_rows + index_increment) % 2 == 0:
        center_columns_indices.append((num_of_rows + index_increment) // 2)
    for i in center_rows_indices:
        for j in center_columns_indices:
            center_points_x.append(coordinates_dict[str(i) + str(j)]['x'])
            center_points_y.append(coordinates_dict[str(i) + str(j)]['y'])
            center_points_z.append(coordinates_dict[str(i) + str(j)]['z'])
    average_x = np.average(np.array(center_points_x))
    average_y = np.average(np.array(center_points_y))
    average_z = np.average(np.array(center_points_z))
    coordinates_dict["center"] = {'x': average_x, 'y': average_y, 'z': average_z}

    return coordinates_dict

pipette_tip_1 = grid_generator(top_left={'x': 237.01, 'y': 52.14, 'z': 20.00, 'e': None, 'speed': None},# done
                                top_right={'x': 235.38, 'y': 13.04, 'z': 20.00, 'e': None, 'speed': None}, # done
                                bottom_left={'x': 173.94, 'y': 48.37, 'z': 20.00, 'e': None, 'speed': None}, # done
                                bottom_right={'x': 172.45, 'y': 11.10, 'z': 20.00, 'e': None, 'speed': None}) # done

pipette_tip_2 = grid_generator(top_left={'x': 235.49, 'y': 5.35, 'z': 20.00, 'e': None, 'speed': None}, # done
                                top_right={'x': 236.02, 'y': -33.54, 'z': 20.00, 'e': None, 'speed': None}, # done
                                bottom_left={'x': 172.50, 'y': 3.91, 'z': 20.00, 'e': None, 'speed': None}, # done
                                bottom_right={'x': 172.37, 'y': -33.03, 'z': 20.00, 'e': None, 'speed': None}, # done
                                index_increment=6)


class ParamterPipette(object):

    def __init__(self, robot_speed=400):
        # roobt setting
        self.robot_speed = robot_speed
        self.pipette_busy = False
        self.PIPETTE_serial_add="COM4"
        self.LA_pump_serial_add = 'COM5'
        self.LA_pump_serial_baud_rate = 9600

        # robot location information
        self.text = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        self.Vial_holder_loc = [[141.30, -132.00], [195.00, -137.00],
                                [143.30, -185.20], [200.10, -190.20], 
                                [148.20, -242.00], [201.30, -242.00],
                                [249.00, -141.10], [249.80, -192.30]]  # 1~8
        self.init_loc = [161.07, 0.0, 37.52]
        self.cuvette_Holder_loc=[84.50, -169.50]
        self.trash_loc = [180.87, 90.05]
        self.pipette_tip = {**pipette_tip_1, **pipette_tip_2}
    

class Pipette(ParamterPipette):
    """
    [Pipette Machine] Pipette Machine Class to control Swift Pro (Robot Arm) + Nema 17 stepper motor (on Arduino)

    This class input logger_obj, so that our class use logging class in this pipette class.
    if you want to consider the law of logging function, please refer Log/Logging_Class.py

    # Variable

    - param logger_obj (obj): set logging object
    - param robot_speed=50000 (int): set swift pro's robot_speed
    - param mode_type="virtual" (str): set virtual or real mode
    
    # function
    - moveLAPump(microVolume=2, mode="pull")
    - disconnectLApump()
    - inject_to_cuvette(swift, vial_pos, pos='A12')
    """    
    def __init__(self, logger_obj, robot_speed=1000000):

        self.logger_obj=logger_obj # make logger_obj
        ParamterPipette.__init__(self,robot_speed=robot_speed) # inherit ParameterPipette
        self.arduinoData = serial.Serial(self.LA_pump_serial_add, self.LA_pump_serial_baud_rate)

    def hello(self,):
        debug_msg="Hello World!! Succeed to connection to main computer!"
        self.logger_obj.debug(device_name="Pipette Machine", debug_msg=debug_msg)

        return debug_msg
        
    def moveLAPump(self, microVolume=2, mode="pull", mode_type="virtual"):
        """
        Arduino Movement (linear actuator with 5ml plastic syringe)

        :param microVolume (int) : pull solution (2 == 200 microliter)
        :param mode (string) : "pull" or "inject"

        :return: status_message
        """
        pump_device_name = "Pipette Machine (LA_pump) ({})".format(mode_type)
        if mode == "pull":
            msg = "Pull out solution"
            if mode_type == "real":
                res=self.arduinoData.write(str(microVolume).encode())
                time.sleep(2)
                self.logger_obj.debug(pump_device_name, msg)
                return res
            elif mode_type == "virtual":
                self.logger_obj.debug(pump_device_name, msg)
        
        elif mode == "inject":
            msg = "Inject solution"
            if mode_type == "real":
                res=self.arduinoData.write(("-" + str(microVolume)).encode())
                time.sleep(2)
                self.logger_obj.debug(pump_device_name, msg)
                return res
            elif mode_type == "virtual":
                self.logger_obj.debug(pump_device_name, msg)
    
    def disconnectLApump(self, mode_type="virtual"):
        """
        Arduino Disconnection (linear actuator with 5ml plastic syringe)

        :param mode_type="virtual" (str): set virtual or real mode

        :return: None
        """
        pump_device_name = "Pipette Machine (LA_pump) ({})".format(mode_type)
        msg = "Disconnect pump"
        if mode_type == "real":
            self.logger_obj.debug(pump_device_name, msg)
            self.arduinoData.close()
        elif mode_type == "virtual":
            self.logger_obj.debug(pump_device_name, msg)

    def inject2Cuvette(self, swift, vial_num, mixing_time=2, pos='A12', mode_type="virtual"):
        """
        receive command_byte & send tcp packet using socket.
        
        This function include pipette tip & cuvette detection using computer vision. 

        :param swift (object) : input swift object type (swift.api)
        :param vial_num (int) : each vial holder location (0~7)
        :param mixing_time=3 (int) : how many times do you mix cuvette solution?
        :param pos='A12' (str) : each pipette tip location
        :param mode_type="virtual" (str): set virtual or real mode

        :return: status_message
        """
        vial_num=int(vial_num)
        robot_device_name = "Pipette Machine (Robot arm) ({})".format(mode_type)
        pump_device_name = "Pipette Machine (LA_pump) ({})".format(mode_type)
        if mode_type == "real":

            # pipette dectection
            pipette_tip_status=0
            while True: # repeat until get the pipette tip
                self.logger_obj.debug(robot_device_name, "Get the pipette tip")
                time.sleep(0.5)
                swift.set_position(x=self.init_loc[0], y=self.init_loc[1], z=self.init_loc[2], speed=self.robot_speed)
                time.sleep(0.5)
                swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=40000)
                time.sleep(0.5)
                swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -78.00, speed=40000)
                time.sleep(0.5)
                swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -89.10, speed=200)
                time.sleep(2)
                swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=40000)
                time.sleep(0.5)

                # inital point
                swift.set_position(x=self.init_loc[0], y=self.init_loc[1], z=self.init_loc[2], speed=self.robot_speed)
                time.sleep(0.5)
                tip_status = detection_real()

                if tip_status==True: # tip detection
                    break
                pipette_tip_status+=1

                if pipette_tip_status==5: # too much error, then stop
                    raise Exception("[Pipette Machine] : There is no tip in tip holder. Please check this status")
                    break

            self.logger_obj.debug(robot_device_name, "Get the pipette tip")
            time.sleep(1)
            swift.set_wrist(180)
            time.sleep(3)
            swift.set_wrist(90)
            time.sleep(3)
            swift.reset(speed=self.robot_speed)
            time.sleep(1)
            self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))
            time.sleep(2)
            swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=self.robot_speed)
            time.sleep(2)
            swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -79.00, speed=40000)
            time.sleep(2)
            # swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -89.50, speed=200) 2022-10-08
            swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -90.00, speed=200)
            time.sleep(2)
            swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=40000)
            # inital point
            time.sleep(2)
            swift.reset(speed=self.robot_speed)
            self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))

            for i in range(2):
                # vial point
                time.sleep(2)
                swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=50.00, speed=self.robot_speed)
                time.sleep(2)
                swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=-63.00, speed=40000)
                time.sleep(2)
                self.moveLAPump(microVolume=2, mode="pull", mode_type=mode_type)
                time.sleep(2)
                self.logger_obj.debug(robot_device_name, "Move vial to cuvette")
                swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=50.00, speed=40000)
            
                # cuvette point
                time.sleep(2)
                swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=50.00, speed=self.robot_speed)

                # change z position more deeper and x,y
                time.sleep(2)
                swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=-42.00, speed=40000)
                time.sleep(2)
                self.moveLAPump(microVolume=2, mode="inject", mode_type=mode_type)
                time.sleep(2)
                swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=50.00, speed=40000)

            # vial point
            self.logger_obj.debug(robot_device_name, "Move vial to cuvette")
            time.sleep(2)
            swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=50.00, speed=self.robot_speed)
            time.sleep(2)
            swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=-63.00, speed=40000)
            time.sleep(2)
            self.logger_obj.debug(pump_device_name, "Inject Solution")
            self.moveLAPump(microVolume=2, mode="pull", mode_type=mode_type)
            time.sleep(2)
            self.logger_obj.debug(robot_device_name, "Move vial to cuvette")
            swift.set_position(x=self.Vial_holder_loc[vial_num][0], y=self.Vial_holder_loc[vial_num][1], z=50.00, speed=40000)

            # cuvette point
            time.sleep(2)
            swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=50.00, speed=self.robot_speed)
            # change z position more deeper and x,y
            time.sleep(2)
            swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=-42.00, speed=40000)
            time.sleep(2)
            for _ in range(mixing_time):
                time.sleep(2)
                self.moveLAPump(microVolume=2, mode="inject", mode_type=mode_type)
                time.sleep(2)
                self.moveLAPump(microVolume=2, mode="pull", mode_type=mode_type)
            time.sleep(2)
            self.moveLAPump(microVolume=2, mode="inject", mode_type=mode_type)
            time.sleep(2)
            self.logger_obj.debug(pump_device_name, "Pump done")
            swift.set_position(x=self.cuvette_Holder_loc[0], y=self.cuvette_Holder_loc[1], z=50.00, speed=40000)

            # Clear tip point
            time.sleep(2.5)
            self.logger_obj.debug(robot_device_name, "Remove the tip")
            swift.set_position(x=self.trash_loc[0], y=self.trash_loc[1], z=50.00, speed=self.robot_speed)
            time.sleep(2)
            swift.set_wrist(180)
            time.sleep(3)
            swift.set_wrist(90)
            time.sleep(3)

            # Initial point
            swift.reset(speed=self.robot_speed)
            self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))

            self.logger_obj.debug(robot_device_name, "UV sample preaparation is done")
            return_res_msg="[{}] : {}".format(robot_device_name, "UV sample preaparation is done")
            return return_res_msg

        elif mode_type == "virtual":
            self.logger_obj.debug(robot_device_name, "Get the pipette tip")
            self.logger_obj.debug(robot_device_name, "Move vial to cuvette")
            self.logger_obj.debug(pump_device_name, "Inject Solution")
            self.logger_obj.debug(pump_device_name, "Mix Solution")
            for i in range(mixing_time):
                self.moveLAPump(microVolume=2, mode="inject")
                time.sleep(2)
                self.moveLAPump(microVolume=2, mode="pull")
            self.logger_obj.debug(pump_device_name, "Pump done")
            self.logger_obj.debug(robot_device_name, "Remove the tip")
            return_res_msg="[{}] : {}".format(robot_device_name, "UV sample preaparation is done")
            return return_res_msg
    
    def test(self, swift, vial_num, pos='A12'):
        """
        receive command_byte & send tcp packet using socket.
        
        This function include pipette tip & cuvette detection using computer vision. 

        :param swift (object) : input swift object type (swift.api)
        :param vial_num (int) : each vial holder location (0~7)
        :param mixing_time=3 (int) : how many times do you mix cuvette solution?
        :param pos='A12' (str) : each pipette tip location

        :return: status_message
        """
        vial_num=int(vial_num)
        robot_device_name = "Pipette Machine (Robot arm) (test)"
        self.logger_obj.debug(robot_device_name, "Get the pipette tip")
        time.sleep(2)
        swift.reset(speed=self.robot_speed)
        time.sleep(2)
        self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))
        time.sleep(2)
        swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=self.robot_speed)
        time.sleep(2)
        swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -79.00, speed=40000)
        time.sleep(2)
        swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'] -89.50, speed=200)
        time.sleep(2)
        swift.set_position(x=self.pipette_tip[pos]['x'], y=self.pipette_tip[pos]['y'], z=self.pipette_tip[pos]['z'], speed=40000)
       
        # inital point
        time.sleep(2)
        self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))
        swift.reset(speed=self.robot_speed)

        # Clear tip point
        self.logger_obj.debug(robot_device_name, "Remove the tip")
        time.sleep(2)
        swift.set_position(x=self.trash_loc[0], y=self.trash_loc[1], z=50.00, speed=self.robot_speed)
        time.sleep(2.5)
        swift.set_wrist(180, wait=True)
        time.sleep(2.5)
        swift.set_wrist(90, wait=True)
        time.sleep(2.5)

        # Initial point
        swift.reset(speed=self.robot_speed)
        self.logger_obj.debug(robot_device_name, "initial point {}".format(swift.get_position()))

        self.logger_obj.debug(robot_device_name, "UV sample preaparation is done")
        return_res_msg="[{}] : {}".format(robot_device_name, "UV sample preaparation is done")
        return return_res_msg