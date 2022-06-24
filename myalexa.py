#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
##############################################################################################
#### BASED ON WORK BY : https://github.com/nassir-malik/IOT-Pi3-Alexa-Automation          ####
##############################################################################################


import sys, re, argparse
import fcntl
import os
import re
import time
import locale
import pigpio
import socket
import signal, atexit, subprocess, traceback
import threading

try:
    from mylog import MyLog
    import fauxmo
    from fauxmo import debounce_handler
except Exception as e1:
    print("\n\nThis program requires the modules located from the same github repository that are not present.\n")
    print("Error: " + str(e1))
    sys.exit(2)


class device_handler(debounce_handler, MyLog):
    """Publishes the on/off state requested,
       and the IP address of the Echo making the request.
    """
    def __init__(self, log=None, shutter=None, config=None):
        self.log = log
        self.shutter = shutter
        self.config = config
        super(device_handler, self).__init__()        
    
    def act(self, client_address, state, name):
        self.LogInfo("--> State " + str(state) + " on " + name + " from client @ " + client_address)
        shutterId = self.config.ShuttersByName[name]
        if state:
           self.shutter.lower(shutterId)
        else:
           self.shutter.rise(shutterId)
        return True


class Alexa(threading.Thread, MyLog, debounce_handler):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name="Alexa")
        self.shutdown_flag = threading.Event()
        
        self.args = args
        self.kwargs = kwargs
        if kwargs["log"] != None:
            self.log = kwargs["log"]
        if kwargs["shutter"] != None:
            self.shutter = kwargs["shutter"]
        if kwargs["config"] != None:
            self.config = kwargs["config"]
        
        # Startup the fauxmo server
        self.poller = fauxmo.poller(log = self.log)
        self.upnp_responder = fauxmo.upnp_broadcast_responder(log = self.log)
        self.upnp_responder.init_socket()
        self.poller.add(self.upnp_responder)

        # Register the device callback as a fauxmo handler
        dbh = device_handler(log=self.log, shutter=self.shutter, config=self.config)
        for shutter, shutterId in sorted(self.config.ShuttersByName.items(), key=lambda kv: kv[1]):
            portId = 50000 + (abs(int(shutterId,16)) % 10000)
            self.LogInfo ("Remote address in dec: " + str(int(shutterId,16)) + ", WeMo port will be n°" + str(portId))
            fauxmo.fauxmo(shutter, self.upnp_responder, self.poller, None, portId, dbh, log=self.log)
                        
        return

    def run(self):
        self.LogInfo("Entering fauxmo polling loop")
        error = 0
        while not self.shutdown_flag.is_set():
            # Loop and poll for incoming Echo requests
            try:
                # Allow time for a ctrl-c to stop the process
                self.poller.poll(100)
                time.sleep(0.01)
            except Exception as e:
                error += 1
                self.LogInfo("Critical exception n°" + str(error) + ": "+ str(e.args))
                print("Trying not to shut down Alexa")
                time.sleep(0.5) #Wait half a second when an exception occurs
#                if(error > 5):
#                    self.LogError("Sixth critical error:" + str(e.args))
#                    break
            
        self.LogError("Received Signal to shut down Alexa thread")
        return

 
