import cherrypy
import paho.mqtt.client as PahoMQTT
import requests
import json
from datetime import datetime
import time

# TODO: add libraries for sensors - need RPi

### Define main class
class DevConn:
    def __init__(self, conf_path, self_path):
        """
        Input parameters:
        - Configuration file (with services catalog location)
        - Information about self
        """
        with open('conf_path') as f:
            self.conf = json.load(f)
            self.sc_addr = self.conf["services_catalog"]["ip"] + str(self.conf["services_catalog"]["port"])

        with open('self_path') as f:
            self.whoami = json.load(f)

        self.dev_cat_info = {}
        self.dev_cat_timestamp = 0
        self.dev_cat_timeout = 120 #s
        self._registered_dev_cat = False

        # Read all available sensors from the 'whoami' dict, initialize suitable
        # device agents

        # !!!! 
        # IDEA: store device agents in a list, plus the corresponding position 
        # in a dictionary having as keys the sensor names
        self.last_meas = []
        self.dev_agents = []
        self.dev_agent_ind = {}
        count = 0
        for elem in self.whoami["resources"]["sensors"]:            
            # Add the 'last measured' field
            for ind in range(len(elem["measure_type"])):
                # NOTE: SenML format
                curr_meas = {
                    "n": elem["measure_type"][ind], 
                    "u": elem["units"][ind],
                    "t": 0,
                    "v": 0
                    }
                self.last_meas.append(curr_meas)

            # TODO: initialize correct objects - need RPi
            # NOTE: Pin numbers are found in the configuration file

            if elem["device_name"] == "DHT11":
                self.dev_agent_ind["DHT11"] = count
                count += 1
                #
                # self.dev_agents.append(DHT11())
                pass
            elif elem["device_name"] == "BMP180":
                self.dev_agent_ind["BMP180"] = count
                count += 1
                # self.dev_agents.append(BMP180())
                pass
        
        self.n_sens = count

    def connectToServCat(self, max_tries):
        """
        connectToServCat
        ----------------------------------------------
        Attempt to contact the services catalog to 
        retrieve information about the device catalog
        ----------------------------------------------
        Parameters:
        - max_tries: max n. of attempts (hint: use 
          high value at the beginning)
        ----------------------------------------------
        Output:
        - 1 if info was correctly retrieved
        - 0 if not
        """
        tries = 0
        while tries <= max_tries and self.dev_cat_info == {}:
            addr = self.sc_addr + "/device_catalog"
            r = requests.get(addr)
            if r.status_code == requests.code.ok:
                self.dev_cat_info = r.json()
                self.dev_cat_timestamp = time.time()
                print("Device catalog info retrieved!")
            else:
                print(f"Error {r.status_code}")
        
        if self.dev_cat_info != {}:
            return 1
        else:
            return 0


    def cleanupDevCat(self):
        """
        cleanupDevCat
        ----------------------------------------------
        Used to clean device catalog records. It uses 
        the attribute 'self.dev_cat_timeout'.
        ----------------------------------------------
        Output:
        - 1: deleted info
        - 0: info still good
        """
        if time.time() - self.dev_cat_timestamp > self.dev_cat_timeout:
            self.dev_cat_info = {}
            self.dev_cat_timestamp = 0
            return 1
        return 0        


    def registerAtDevCat(self, max_tries):
        """
        registerAtDevCat
        ----------------------------------------------
        Used to register at the device catalog
        ----------------------------------------------
        Parameters:
        - max_tries
        ----------------------------------------------
        Output:
        - 1: success
        - 0: unable to register - can't reach cat
        - -1: missing dev. cat. info
        """
        tries = 0
        if self.dev_cat_info != {}:
            while tries <= max_tries and not self._registered_dev_cat:
                addr_dev_cat = self.dev_cat_info["ip"] + str(self.dev_cat_info["port"])
                addr = addr_dev_cat + "/device"
                r = requests.post(addr, data=self.whoami)
                if r.status_code == requests.code.ok:
                    self.dev_cat_info = r.json()
                    print("Registered!")
                else:
                    print(f"Error {r.status_code}")
            
            if self.dev_cat_info != {}:
                return 1
            else:
                return 0
        else: 
            print("Missing device catalog info!")
            return -1


    def updateDevCat(self, max_tries):
        tries = 0
        if self.dev_cat_info != {}:
            while tries <= max_tries and not self._registered_dev_cat:
                addr_dev_cat = self.dev_cat_info["ip"] + str(self.dev_cat_info["port"])
                addr = addr_dev_cat + "/device"
                r = requests.put(addr, data=self.whoami)
                if r.status_code == requests.code.ok:
                    self.dev_cat_info = r.json()
                    print("Registered!")
                elif r.status_code == 400:  # From dev. cat.: if unable to update, the return code is 400
                    # Try to POST
                    if self.registerAtDevCat() == 1:
                        print("Had to register!")
                        return 1
                else:
                    print(f"Error {r.status_code}")
            
            if self.dev_cat_info != {}:
                return 1
            else:
                return 0
        else: 
            return -1




### Main program - include loop

if __name__ == "__main__":
    pass