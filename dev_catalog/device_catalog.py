import cherrypy
import requests
import json
import time
from datetime import datetime

"""
Device Catalog
---------------------------------------
This program contains the Device 
Catalog for our application 
---------------------------------------
Running on localhost, need to change 
port if running along the service 
catalog (on port 8080)
"""

class DeviceCatalog():
    """
    DeviceCatalog
    ---------------------------------------
    This class defines the main methods and
    attributes of the device catalog.
    The web service will use an instance of
    DeviceCatalog to handle the JSON 
    catalog.
    """

    def __init__(self, in_path, serv_catalog_info="serv_cat_info.json", out_path="dev_cat_updated.json"):
        # Allow to use fac-simile catalog for testing
        try:
            self.cat = json.load(open(in_path))
        except:
            print("Default device catalog taken")
            self.cat = json.load(open("dev_catalog.json"))
        
        self._dev_cat_params = ['project_name', 'project_owner', 
                        'device_catalog', "devices"]

        # Check for valid catalog
        if all(elem for elem in self.cat for elem in self._dev_cat_params):
            print("Valid catalog!")
        else:
            raise KeyError("Wrong device catalog syntax!")
        
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # For checking at insertion:
        self._device_params = ['id', 'name', 'endpoints', 
                            'endpoints_details', 'greenhouse', 
                            'resources', 'last_update']
        
        self.out_path = out_path







"""
This stuff goes into the webservice

        # TODO: Connect and register to service catalog
        # POST request
        try:
            self._serv_cat = json.load(open(serv_catalog_info))
        except:
            print("Default service catalog information taken!")
            self._serv_cat = json.open(open("serv_cat_info.json"))

        # For sure the service catalog is a WebService; get its address
        self._serv_cat_addr = self._serv_cat["ip"]+':'+str(self._serv_cat["port"])"""
