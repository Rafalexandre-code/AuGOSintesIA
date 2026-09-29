#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ##
# @brief    [UVServer] UVServer included Pipette Machine + Linear Actuator in Autonomous Laboratory
# @author   Hyuk Jun Yoo (yoohj9475@kist.re.kr)   
# TEST 2021-09-24
# TEST 2022-03-24

from UV.UV_Class import USB2000plus_Class
from Pipette_Machine.Pipette_Class import Pipette
from Pipette_Machine.uarm.wrapper.swift_api import SwiftAPI
from Log.Logging_Class import NodeLogger
from BaseUtils.TCP_Node import BaseTCPNode
import socket
import time

SIZE = 1048576

# # TCP/IP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('161.122.22.80', 54009))  # ip address, port
server_socket.listen()  # wait status requirement of client connection

NodeLogger_obj = NodeLogger(platform_name="UV Platform", setLevel="DEBUG",
                            SAVE_DIR_PATH="C:/Users/User/Desktop/UVPlatform")

UV_obj = USB2000plus_Class(NodeLogger_obj)
Pipette_obj = Pipette(NodeLogger_obj)
swift = SwiftAPI(port=Pipette_obj.PIPETTE_serial_add)

base_tcp_node_obj = BaseTCPNode()

try:
    while True:
        client_socket, addr = server_socket.accept()  # accept connection. return ip, port 
        data = client_socket.recv(SIZE)  # recieve data from client. print buffer size
        packet_info = str(data.decode()).split(sep="/")
        print("packet information list : ", packet_info)
        time.sleep(1)

        if packet_info[0] == "UV":
            hardware_name, action_type, mode_type = packet_info
            res_msg = UV_obj.getUVData(client_socket, action_type, mode_type=mode_type)
            base_tcp_node_obj.checkSocketStatus(client_socket, res_msg, hardware_name, action_type=action_type)

        elif packet_info[0] == "PIPETTE":
            hardware_name, action_type, vial_num, tip_position, mode_type = packet_info
            res_msg = Pipette_obj.inject2Cuvette(swift, vial_num=vial_num, pos=tip_position, mode_type=mode_type)
            base_tcp_node_obj.checkSocketStatus(client_socket, res_msg, hardware_name, action_type)

        elif packet_info[0] == "OPTICS":
            hardware_name, action_type, _ = packet_info
            total_dict={}
            total_dict["Pipette machine"]=Pipette_obj.hello()
            total_dict["Ocean optics"]=UV_obj.hello()
            base_tcp_node_obj.checkSocketStatus(client_socket, total_dict, hardware_name, action_type)
        else:
            raise ValueError("[{}] Packet Error : hardware_name is wrong".format(hardware_name))
            
except KeyboardInterrupt:
    print('Ctrl + C, interrupt message')