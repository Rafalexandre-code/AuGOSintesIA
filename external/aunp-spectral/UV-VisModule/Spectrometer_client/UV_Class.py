#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ##
# @brief    [UV Spectroscopy] motion basic class for UV Spectroscopy (USB2000+)
# @author   Hyuk Jun Yoo (yoohj9475@kist.re.kr)   
# TEST 2021-09-23

import socket
import json
import os, sys
import time
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from BaseUtils.Preprocess import PreprocessJSON
from BaseUtils.TCP_Node import BaseTCPNode

class ParameterUV:
    """
    Linear Actuator IP, PORT, location dict, move_z

    :param self.WINDOWS1_HOST = '161.122.22.146'  # The server's hostname or IP address
    :param self.PORT_UV = 54011       # The port used by the UV server (54011)
    """
    def __init__(self):
        self.UV_info={
            "HOST_UV" : "127.0.0.1",
            "PORT_UV" : 54011
        }


class USB2000plus_Class(ParameterUV, BaseTCPNode, PreprocessJSON):
    """
    [USB2000+] USB2000+ Class for controlling in another computer (windows)

    # Variable
    :param logger_obj (obj): set logging object (from Logging_class import Loggger) 
    :param device_name="USB2000plus" (str): set UV model name (log name) 
    :param mode_type="virtual" (str): set virtual or real mode
    
    # function
    - hello()
    - get_Abs_data(client_socket, action_type, mode_type)
    """
    def __init__(self, logger_obj, device_name="USB2000plus"):
        ParameterUV.__init__(self,)
        BaseTCPNode.__init__(self,)
        PreprocessJSON().__init__()
        self.logger_obj=logger_obj
        self.device_name = device_name

    def _callServer_UV(self, command_byte):
        res_msg=self.callServer(self.UV_info["HOST_UV"], self.UV_info["PORT_UV"], command_byte)
        return res_msg

    def hello(self):
        """
        get connection status using TCP/IP (socket)
        
        :return res_msg (str): "Hello World!! Succeed to connection to main computer!"
        """
        debug_device_name="{} ({})".format(self.device_name, "hello")

        command_byte = str.encode("{},{}".format("hello", "status"))
        res_msg=self._callServer_UV(command_byte)

        self.logger_obj.debug(device_name=debug_device_name, debug_msg=res_msg)

        return res_msg
       
    def getUVData(self, client_socket, action_type, mode_type="virtual"):
        """
        get Absorbance data using TCP/IP (socket)
        
        :param client_socket (str): input sockect object (main computer)
        :param action_type (str): chemical element (Ag,Au....)
        :param mode_type="virtual" (str): set virtual or real mode

        :return res_msg (bool): response_message --> [UV] : ~~~
        """
        debug_device_name="{} ({})".format(self.device_name, mode_type)
        self.logger_obj.debug(device_name=debug_device_name, debug_msg="start get {} data".format(action_type))

        # if mode_type == "real":
        command_byte = str.encode("{},{}".format(action_type, "NP"))

        # get json file name through UV server
        file_name_decoded=self._callServer_UV(command_byte)

        # open json content using open function
        total_json = self.openJSON(filename=file_name_decoded)
        ourbyte = self.encodeJSON(json_obj=total_json)

        # send big json file using parsing
        if len(ourbyte) > self.BUFF_SIZE:
            self._sendTotalJSON(client_socket=client_socket, ourbyte=ourbyte)
        else:
            client_socket.sendall(json.dumps(total_json).encode("utf-8"))
        
        # send finish message to main computer
        time.sleep(3)
        finish_msg="finish"
        client_socket.sendall(finish_msg.encode())

        self.logger_obj.debug(device_name=debug_device_name, debug_msg=finish_msg)
        return_res_msg="[{}] : {}".format(debug_device_name, finish_msg)
        return return_res_msg
            
        # elif mode_type == "virtual":
        #     command_byte = str.encode("{},{}".format(action_type, "NP"))
        #     file_name_decoded=self._callServer_UV(command_byte=command_byte)
        #     if file_name_decoded == False:
        #         return False
        #     else:
        #         res_msg="Succed to analysis: {}".format(file_name_decoded).encode() # substitute that message (because of return message is filename)
        #         client_socket.sendall(res_msg)
        #         time.sleep(2)
        #         res_msg="finish".encode() # substitute that message (because of return message is filename)
        #         client_socket.sendall(res_msg)
        #         return_res_msg="[{}] : {}".format(debug_device_name, res_msg)
        #         self.logger_obj.debug(device_name=debug_device_name, debug_msg=res_msg)
        #         return return_res_msg
    

if __name__ == "__main__":

    import os, sys
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../Log")))  # get import path : Logging_Class.py
    from Log.Logging_Class import Logger
    log_obj=Logger()
    usb_obj=USB2000plus_Class(logger_obj=log_obj, mode_type="real")
    usb_obj.get_Abs_data()