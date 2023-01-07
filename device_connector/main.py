import cherrypy
import paho.mqtt.client as PahoMQTT
import requests
import json
from datetime import datetime
import time
from sub.MyMQTT import MyMQTT

# TODO: add libraries for sensors - need RPi


def searchListOfDict(lst, parameter, value):
    """
    Used to search for elements inside a list of dictionaries
    `lst`.
    The search is performed over key `parameter`, having value 
    `value`.
    If found, return it, else return None
    """
    for elem in lst:
        if elem[parameter] == value:
            return elem
    return None


### Define main class
class DevConn:
    def __init__(self, conf_path, self_path):
        """
        Input parameters:
        - Configuration file (with services catalog location)
        - Information about self
        """
        with open(conf_path) as f:
            self.conf = json.load(f)
            self.sc_addr = self.conf["services_catalog"]["ip"] + str(self.conf["services_catalog"]["port"])

        with open(self_path) as f:
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
        # The program does not know in advance which sensors it has!
        self.last_meas = []
        self.dev_agents_sens = []
        self.dev_agent_ind_sens = {}
        count = 0
        for elem in self.whoami["resources"]["sensors"]:            
            # Add the 'last measured' field
            # Iterate over the measure_type list

            # Sensors can measure different quantities - each sensor is 
            # associated to a sub-list in `self.last_meas`.
            
            # `self.last_meas` follows the same indexing as `self.dev_agents_sens`
            sens_meas_sublist = []
            for ind in range(len(elem["measure_type"])):
                # NOTE: SenML format
                # Assume no sensors measure the same quantity 
                # (if 2 sensors measure the same quantity, then
                # one always covers the other)
                curr_meas = {
                    "n": elem["measure_type"][ind], 
                    "u": elem["units"][ind],
                    "t": 0,
                    "v": 0
                    }

                if searchListOfDict(sens_meas_sublist, "n", curr_meas["n"]) is None:
                    sens_meas_sublist.append(curr_meas)
            
            self.last_meas.append(sens_meas_sublist)

            # TODO: initialize correct objects - need RPi
            # NOTE: Pin numbers are found in the configuration file

            if elem["device_name"] == "DHT11":
                self.dev_agent_ind_sens["DHT11"] = count
                count += 1
                # Here one can add the specific instantiations of the device agents
                #
                # self.dev_agents_sens.append(DHT11())
                pass
            elif elem["device_name"] == "BMP180":
                self.dev_agent_ind_sens["BMP180"] = count
                count += 1
                # self.dev_agents_sens.append(BMP180())
                pass
        
        self.n_sens = count

        # Same thing but for actuators:
        self.dev_agents_act = []
        self.dev_agent_ind_act = {}
        count = 0
        for elem in self.whoami["resources"]["actuators"]:
            # if elem["name"] == "ACT00":
                # self.dev_agent_ind["ACT00"]  = count
                # count += 1
                # self.dev_agents_act.append(ACT00())
            pass


        ######## MQTT client
        # Get broker information
        self.broker_info = {}           # No timestamp - suppose it does not change
        
        while self.broker_info == {}:
            if self.getBrokerInfo(max_tries=500) != 1:
                print("Cannot get broker info!")

        self.mqtt_cli = MyMQTT(
            clientID=self.whoami["name"], 
            broker=self.broker_info["ip"],
            port=self.broker_info["port_n"],
            notifier=self
            )

        # Connect to the broker
        self.mqtt_cli.start()

        # Subscribe to the topics used for control the actuators
        # The topics are stored in the list `act_topics`
        act_topics = []
        for elem in self.whoami["resources"]["actuators"]:
            if "MQTT" in elem["available_services"]:
                for top in elem["service_details"]["topic"]:
                    act_topics.append(top)
                    self.mqtt_cli.mySubscribe(top)
        



    #TODO
    ##################################################################
    def notify(self, topic, payload):
        """
        Callback for the MyMQTT object
        When a message is received in either of the 
        topics related to the actuators, it acts on them.
        """
        # Read message
        # Depending on the topic and content, choose the right action

        # Find right actuator depending on topic
        for act in self.whoami["resources"]["actuators"]:
            if "MQTT" in act["available_services"]:
                if topic in act["service_setails"]:
                    # Found correct device!
                    # ...
                    pass

        pass
    ##################################################################



    def getBrokerInfo(self, max_tries):
        tries = 0
        while tries <= max_tries and self.broker_info == {}:
            addr = self.sc_addr + "/broker"
            r = requests.get(addr)
            if r.status_code == requests.code.ok:
                self.broker_info = r.json()
                print("Device catalog info retrieved!")
            else:
                print(f"Error {r.status_code}")
        
        if self.broker_info != {}:
            return 1
        else:
            return 0


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


    def updateMeas(self):
        # Read all available services and update self.last_meas

        for sensname in self.dev_agent_ind_sens:
            # Each device agent must have a method 'measure()'
            # `curr_meas` is already a SenML-formatted Python dictionary
            curr_meas = self.dev_agents_sens[self.dev_agent_ind_sens[sensname]].measure()
            
            # Find the correct sublist containing the last measurement for the sensor 
            # and place the current measurement inside

            # curr_meas can be either a single dict (same device used to 
            # measure multiple quantities) or a list of dicts
            if isinstance(curr_meas, dict):
                self.last_meas[self.dev_agent_ind_sens[sensname]] = [curr_meas]
            
            elif isinstance(curr_meas, list):
                self.last_meas[self.dev_agent_ind_sens[sensname]] = curr_meas

    
    def publishLastMeas(self):
        # Read all sensor topics from "self.whoami"
        # Find the last measured value for the specific quantity (use indexing in `self.dev_agent_ind_sens`)
        # Publish it in the correct topic
        pass



### Main program - include loop

if __name__ == "__main__":
    
    myDevConn = DevConn("./conf_dev_conn.json", "./dev_info.json")
    