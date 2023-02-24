import cherrypy
import paho.mqtt.client as PahoMQTT
import requests
import json
from datetime import datetime
import time
import warnings
from sub.MyMQTT import MyMQTT

from device_agents.dht11_agent import DHT11Agent
from device_agents.bmp180_agent import BMP180Agent
from device_agents.bh1750_agent import BH1750Agent
from device_agents.keyes_srly_agent import KeyesSRLYAgent

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

        # NOTE: store device agents in a list, plus the corresponding position 
        # in a dictionary having as keys the sensor ID
        
        # The program does not know in advance which sensors it has!
        self.last_meas = []
        self.dev_agents_sens = []
        self.dev_agent_ind_sens = {}
        count = 0
        for elem in self.whoami["resources"]["sensors"]:            
            # Add the 'last measured' field
            # Iterate over the measure_type list

            # Sensors can measure more than one quantity - each sensor is 
            # associated to a sub-list in `self.last_meas`.
            
            # `self.last_meas` follows the same indexing as `self.dev_agents_sens`
            sens_meas_sublist = []
            for ind in range(len(elem["measure_type"])):
                # NOTE: SenML format
                
                # Is it?
                """# Assume no sensors measure the same quantity 
                # (if 2 sensors measure the same quantity, then
                # one always covers the other)"""

                curr_meas = {
                    "n": elem["measure_type"][ind], 
                    "u": elem["units"][ind],
                    "t": 0,
                    "v": 0
                    }

                # Prevent from adding more than once the same measured quantity
                # Append the current last measurement for the specified quantity 
                # only if the same quantity is not already present in the sub list
                ############## probably can be removed
                # NOTE: different sublists can include the same measurement
                if searchListOfDict(sens_meas_sublist, "n", curr_meas["n"]) is None:
                    sens_meas_sublist.append(curr_meas)
            
            self.last_meas.append(sens_meas_sublist)

            #####################################################
            # NOTE: Pin numbers are found in the configuration file

            if elem["device_name"] == "DHT11":
                # EXAMPLE:
                self.dev_agent_ind_sens[str(elem["id"])] = count
                count += 1

                # Check availability of conf information
                found = False
                dht_conf = None
                for sens_conf in self.conf["sens_pins"]:
                    if sens_conf["id"] == elem["id"]:
                        dht_conf = sens_conf.copy()
                        found = True
                
                if found:
                    self.dev_agents_sens.append(DHT11Agent(dht_conf))
                else:
                    raise ValueError("The configuration file is missing DHT11 information!")

            elif elem["device_name"] == "BMP180":
                self.dev_agent_ind_sens[str(elem["id"])] = count
                count += 1

                # Check availability of conf information
                found = False
                bmp_conf = None
                for sens_conf in self.conf["sens_pins"]:
                    if sens_conf["id"] == elem["id"]:
                        bmp_conf = sens_conf.copy()
                        found = True

                if found:
                    self.dev_agents_sens.append(BMP180Agent(bmp_conf))
                else:
                    raise ValueError("The configuration file is missing DHT11 information!")
            
            elif elem["device_name"] == "BMP180":
                self.dev_agent_ind_sens[str(elem["id"])] = count
                count += 1

                # Check availability of conf information
                found = False
                bmp_conf = None
                for sens_conf in self.conf["sens_pins"]:
                    if sens_conf["id"] == elem["id"]:
                        bh_conf = sens_conf.copy()
                        found = True

                if found:
                    self.dev_agents_sens.append(BH1750Agent(bh_conf))
                else:
                    raise ValueError("The configuration file is missing BH1750 information!")
            #####################################################
        
        self.n_sens = count     # Total number of sensors

        ################################################
        # Same thing but for actuators
        
        # Each actuator device agent is appended to the list self.dev_agents_act
        # The corresponding positional index is saved as the value of the key 
        # corresponding with the ID of the actuator
        self.dev_agents_act = []
        self.dev_agent_ind_act = {}
        count = 0
        for elem in self.whoami["resources"]["actuators"]:
            if elem["name"] == "Keyes_SRLY":             
                self.dev_agent_ind_act[str(elem["id"])] = count
                count += 1                          

                # Check availability of conf information
                # Fundamental, since multiple actuators can have 
                # the same name, but must be on different pins
                found = False
                myact_conf = None
                for act_conf in self.conf["act_pins"]:
                    if act_conf["id"] == elem["id"]:
                        myact_conf = sens_conf.copy()
                        found = True

                if found:
                    self.dev_agents_act.append(KeyesSRLYAgent(conf=myact_conf))
                else:
                    raise ValueError("The configuration file is missing Keyes_SRLY information!")

        ################################################


        ######## MQTT client
        # Get broker information
        self.broker_info = {}           # No timestamp - suppose it does not change
        
        while self.broker_info == {}:
            if self.getBrokerInfo(max_tries=500) != 1:
                print("Cannot get broker info!")

        # MQTT publisher base name
        self.mqtt_bn = self.whoami["name"] + '_' + str(self.whoami["id"])

        self.mqtt_cli = MyMQTT(
            clientID=self.mqtt_bn,    # Devices can have same name, but must not have same id
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
        ---------------------------------------------------
        The payload is a string in json format
        """
        # Read message
        # Depending on the topic and content, choose the right action
        
        message = json.loads(payload)

        # Find right actuator depending on topic
        for act in self.whoami["resources"]["actuators"]:
            # Check MQTT is supported
            if "MQTT" in act["available_services"]:
                # Check there are available topics (may be unnecessary, but prevent errors in conf)
                if "topic" in act["service_details"].keys():
                    # Find the actuator associated with the specified topic
                    if topic == act["service_details"]["topic"]:
                        
                        # Locate the position of the correct device agent in the list
                        # 'dev_agents_act' via the dictionary 'self_agent_ind_act'

                        # Payload may be either 'start' or 'stop' - this method will 
                        # 'blindly' call the associated method on the device agent
                        index = self.dev_agent_ind_act[str(act["id"])]
                        if message["cmd"] == "start":
                            if self.dev_agent[index].isOn() == False:
                                self.dev_agent[index].start()
                                print(f"Actuator {act['id']} was turmed on at time {message['t']}")
                            else:
                                print(f"Tried to turn on actuator {act['id']}, but it was on!")
                        elif message["cmd"] == "stop":
                            if self.dev_agent[index].isOn() == True:
                                self.dev_agent[index].stop()
                                print(f"Actuator {act['id']} was turmed off at time {message['t']}")
                            else:
                                print(f"Tried to turn off actuator {act['id']}, but it was off!")
                    
                    # May need more customization, e.g., turn on for a specified period
                    # but this must be handled by the corresponding strategy
                
    ##################################################################



    def getBrokerInfo(self, max_tries=50):
        """
        Obtain the broker information from the services catalog.
        ----------------------------------------------------------
        Need to specify the maximum number of tries (default 50).
        ----------------------------------------------------------
        Return values:
        - 1: information was correctly retrieved and is stored in
        attribute self.broker_info
        - 0: the information was not received (for how the 
        services catalog is implemented, it means that it was not
        possible to reach it)
        ----------------------------------------------------------
        """
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


    def connectToServCat(self, max_tries=50):
        """
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


    def registerAtDevCat(self, max_tries=50):
        """
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
                    self._registered_dev_cat = True
                    print("Registered!")
                else:
                    print(f"Error {r.status_code}")
            
            if self._registered_dev_cat:
                # Success
                return 1
            else:
                # Not registered
                return 0
        else: 
            print("Missing device catalog info!")
            return -1


    def updateDevCat(self, max_tries = 50):
        """
        Update own information at device catalog
        ----------------------------------------------------------
        The user can set the max. number of tries.
        If the response to the HTTP request used to contact the 
        device catalog was 400, i.e., unable to update - old 
        record not found, the method 'registerAtDevCat' will be 
        used to register the information.
        ----------------------------------------------------------
        Return value:
        - 1: successful update (also if it was needed to register)
        - 0: unable to reach server
        - -1: missing device catalog information
        """
        tries = 0
        if self.dev_cat_info != {}:
            upd_succ = False
            while tries <= max_tries and not upd_succ:
                addr_dev_cat = self.dev_cat_info["ip"] + str(self.dev_cat_info["port"])
                addr = addr_dev_cat + "/device"
                r = requests.put(addr, data=self.whoami)
                if r.status_code == requests.code.ok:
                    self.dev_cat_info = r.json()
                    print("Registered!")
                elif r.status_code == 400:  # From dev. cat.: if unable to update, the return code is 400
                    # Try to POST
                    self._registered_dev_cat = False
                    if self.registerAtDevCat() == 1:
                        print("Had to register!")
                        return 1
                else:
                    print(f"Error {r.status_code}")
            
            if upd_succ:
                # Success
                return 1
            else:
                # Not updated - can't reach server
                return 0
        else: 
            # Missing catalog info
            return -1


    def updateMeas(self):
        # Read all available services and update self.last_meas

        for sens_id in self.dev_agent_ind_sens.keys():
            # sens_id is already a string

            # Each device agent must have a method 'measure()'
            # `curr_meas` is already a SenML-formatted Python dictionary
            # OR list of dictionaries
            curr_meas = self.dev_agents_sens[self.dev_agent_ind_sens[sens_id]].measure()
            
            # Find the correct sublist containing the last measurement for the sensor 
            # and place the current measurement inside

            # curr_meas can be either a single dict (same device used to 
            # measure multiple quantities) or a list of dicts

            ## TODO: decide what to do with None values returned by the agents if
            # it was not possible to neasure the quantity.
            if isinstance(curr_meas, dict):
                self.last_meas[self.dev_agent_ind_sens[sens_id]] = [curr_meas]

                if curr_meas["v"] is None:
                    raise warnings.warn(f"Null {curr_meas['n']} measurement at {curr_meas['t']}")
            
            elif isinstance(curr_meas, list):
                self.last_meas[self.dev_agent_ind_sens[sens_id]] = curr_meas

                for meas in curr_meas:
                    if meas["v"] is None:
                        raise warnings.warn(f"Null {meas['n']} measurement at {meas['t']}")

    
    def publishLastMeas(self):
        # Read all sensor topics from "self.whoami"
        # Find the last measured value for the specific quantity 
        # (use indexing in `self.dev_agent_ind_sens`)
        for sens in self.whoami["resources"]["sensors"]:
            if "MQTT" in sens["available_services"]:
                # Retrieve last measurements via the name-index mapping
                meas_lst = self.last_meas[self.dev_agent_ind_sens[int(sens["id"])]]

                # Find available topics
                for det in sens["service_details"]:
                    if det["service_type"] == "MQTT":
                        topics_lst = det["topic"]

                        # Publish it in the correct topic
                        # The correct topic contains as last element in the path the 
                        # name of the measured quantity in lowercase, with spaces 
                        # replaced by underscores
                        for meas in meas_lst:
                            meas_qty = meas["n"]
                            
                            # Find topic - the last element in the topic URI must be the measure name 
                            # (lowercase, with '_' instead of ' ')
                            for top_iter in topics_lst:
                                if top_iter.lower().endswith(meas_qty.lower().replace(' ', '_')):
                                    msg = {"bn":self.mqtt_bn, "e": [meas]}
                                    self.mqtt_cli.myPublish(topic=top_iter, msg=msg)
        
        # Keep in mind: can use wildcards (at subscriber) to obtain all measurements
        # for a single parameter if it is measured by multiple sensors



### Main program - include loop

if __name__ == "__main__":
    
    myDevConn = DevConn("conf_dev_conn.json", "dev_info.json")
    
    ############### Start operation ###############

    ok = False
    max_iter_init = 10
    iter_init = 0

    while not ok:
        myDevConn.connectToServCat(max_tries=100)
        init_status = myDevConn.registerAtDevCat(max_tries=100)

        if init_status == 1:
            # Correctly registered
            ok = True
        elif init_status == 0:
            iter_init += 1
        elif init_status == -1:
            # No dev. cat. info
            iter_init += 1
            myDevConn.connectToServCat()

        if iter_init >= max_iter_init:
            # If too many tries - wait some time, then retry
            iter_init = 0
            time.sleep(10)

    ############### Working loop ###############
    while True:
        # Update info
        upd_oper = myDevConn.updateDevCat()
        
        if upd_oper == -1:
            # No dev cat info
            myDevConn.connectToServCat()
            upd_oper = myDevConn.updateDevCat()
        
        # No `elif` - upd_oper was updated
        if upd_oper == 0:
            # Cannot reach device catalog
            print("Cannot reach device catalog!")
            
            max_it = 5
            it = 0
            while upd_oper != 1 and it < max_it:
                time.sleep(5)   # Wait 5s
                upd_oper = myDevConn.updateDevCat()
                it += 1

        # Make and publish measurements
        myDevConn.updateMeas()
        myDevConn.publishLastMeas()

        # Clean possibly old info
        myDevConn.cleanupDevCat()