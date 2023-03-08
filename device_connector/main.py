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
from device_agents.chirp_agent import ChirpAgent
from device_agents.hx711_agent import HX711Agent

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


### Main class definition
class DevConn:
    """
    Device connector class.
    -----------------------------------------------------------------------------
    Attributes:
    - conf: configuration file including the static services catalog info and 
    pin information about the available sensors and actuators
    - sc_addr: services catalog static address
    - whoami: dictionary including the information which is advertised by the 
    device catalog
    - dev_cat_info: dict containing the information about the device catalog 
    (IP, port, ...). It is initialized and reset (timeout) as {}.
    - dev_cat_timestamp: timestamp for the last device catalog update (at the 
    device connector). Note: different from the one found in the non-empty 
    device catalog info, since that one is set by the services catalog.
    - dev_cat_timeout: timeout period for the device catalog information.
    - _registered_dev_cat: flag indicating whether the device is registered 
    at the device catalog
    - last_meas: list of sub-lists containing all the last good measureents 
    from each sensor
    - dev_agents_sens: list of device agents for the sensors
    - dev_agent_ind_sens: dictionary to map the device ID to the associated 
    elements in 'last_meas' and 'dev_agents_sens'
    - all_meas_types: list containing all possible measurements that the 
    device can provide
    - n_sens: number of connected sensors
    - dev_agents_act: list of device agents objects for actuators
    - dev_agent_ind_act: dictionary used to map actuator IDs to the corresponding 
    index in 'dev_agents_act'
    - broker_info: dictionary containing the information of the MQTT broker, 
    retrieved from the services catalog. Initialized as {}
    - mqtt_bn: MQTT client identifier
    - mqtt_cli: MyMQTT object used to create the MQTT client
    - act_topics: list of topics associated with the actuators (to which the 
    client is subscribed)
    -----------------------------------------------------------------------------
    """
    exposed = True

    def __init__(self, conf_path, self_path, own_ID=False):
        """
        Initialization procedure: 
        - For each sensor, instantiate the sublists containing the latest measurements
        - For each sensor, instantiate the device agent
        - For each actuator, instantiate device agent
        - Get broker information from services catalog
        - Instantiate MyMQTT object
        - Subscribe to the topics for the actuators
        ---
        Input parameters:
        - Configuration file (with services catalog location)
        - Information about self
        """
        with open(conf_path) as f:
            self.conf = json.load(f)
            self.sc_addr = "http://" + self.conf["services_catalog"]["ip"] + ":" + str(self.conf["services_catalog"]["port"])

        with open(self_path) as f:
            self.whoami = json.load(f)

        self.dev_cat_info = {}
        self.dev_cat_timestamp = 0
        self.dev_cat_timeout = 120 #s
        self._registered_dev_cat = False

        # NOTE: it can be useful to statically assign device IDs - if the flag own_ID
        # is true, the device will use the ID specified in the conf file
        if not own_ID:
            self._id_assigned = False       # To be set to True iff the new ID was retrieved from device catalog (register)
        else: 
            self._id_assigned = True

        self._http_conf = {
                '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True
                }
            }

        # Read all available sensors from the 'whoami' dict, initialize suitable
        # device agents

        # NOTE: store device agents in a list, plus the corresponding position 
        # in a dictionary having as keys the sensor ID
        
        # The program does not know in advance which sensors it has!
        self.last_meas = []
        self.dev_agents_sens = []
        self.dev_agent_ind_sens = {}
        self.all_meas_types = []
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
                
                meas_uri = elem["measure_type"][ind].lower().replace(' ', '_')
                if meas_uri not in self.all_meas_types:
                    self.all_meas_types.append(meas_uri)

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
                # NOTE: different sublists still can include the same measurement
                if searchListOfDict(sens_meas_sublist, "n", curr_meas["n"]) is None:
                    sens_meas_sublist.append(curr_meas)
            
            self.last_meas.append(sens_meas_sublist)

            #####################################################

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
                    raise ValueError(f"The configuration file is missing sensor {elem['id']} - DHT11 - information!")

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
                    raise ValueError(f"The configuration file is missing sensor {elem['id']} - DHT11 - information!")
            
            elif elem["device_name"] == "BH1750":
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
                    raise ValueError(f"The configuration file is missing sensor {elem['id']} - BH1750 - information!")

            # Soil moisture sensor   
            elif elem["device_name"] == "chirp":
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
                    self.dev_agents_sens.append(ChirpAgent(bh_conf))
                else:
                    raise ValueError(f"The configuration file is missing sensor {elem['id']} - chirp - information!")
            
            # Load cells
            elif elem["device_name"] == "HX711":
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
                    self.dev_agents_sens.append(HX711Agent(bh_conf))
                else:
                    raise ValueError(f"The configuration file is missing sensor {elem['id']} - HX711 - information!")
            #####################################################
        
        self.n_sens = count     # Total number of sensors

        print(self.all_meas_types)
        
        ################################################
        # Same thing but for actuators
        
        # Each actuator device agent is appended to the list self.dev_agents_act
        # The corresponding positional index is saved as the value of the key 
        # corresponding with the ID of the actuator
        self.dev_agents_act = []
        self.dev_agent_ind_act = {}
        count = 0
        for elem in self.whoami["resources"]["actuators"]:
            if elem["device_name"] == "Keyes_SRLY":             
                self.dev_agent_ind_act[str(elem["id"])] = count
                count += 1                          

                # Check availability of conf information
                # Fundamental, since multiple actuators can have 
                # the same name, but must be on different pins
                found = False
                myact_conf = None
                for act_conf in self.conf["act_pins"]:
                    if act_conf["id"] == elem["id"]:
                        myact_conf = act_conf.copy()
                        found = True

                if found:
                    self.dev_agents_act.append(KeyesSRLYAgent(conf=myact_conf))
                else:
                    raise ValueError(f"The configuration file is missing actuator {elem['id']} - Keyes_SRLY - information!")

        ################################################
        ######## MQTT client
        # Get broker information
        self.broker_info = {}           # No timestamp - suppose it does not change
        
        while self.broker_info == {}:
            if self.getBrokerInfo(max_tries=500) != 1:
                print("Cannot get broker info!")

        # MQTT publisher base name
        for ed in self.conf["device_connector"]["endpoints_details"]:
            if ed["endpoint"] == "MQTT":
                self.mqtt_bn = ed["bn"]

        self.mqtt_cli = MyMQTT(
            clientID=self.mqtt_bn,    # Devices can have same name, but must not have same id
            broker=self.broker_info["ip"],
            port=self.broker_info["port_n"],
            notifier=self
            )

        # Connect to the broker
        self.mqtt_cli.start()

        time.sleep(5)   # Wait 5 seconds to allow clean connection

        # Subscribe to the topics used for control the actuators
        # The topics are stored in the list `act_topics`
        self.act_topics = []
        for elem in self.whoami["resources"]["actuators"]:
            if "MQTT" in elem["available_services"]:
                for av_serv in elem["services_details"]:
                    if av_serv["service_type"] == "MQTT":
                        for top in av_serv["topic"]:
                            self.act_topics.append(top)
                            self.mqtt_cli.mySubscribe(top)

    ##################################################################
    # Web service - REST methods definition

    def GET(self, *uri, **params):
        """
        Used to get last measurements, depending on the URI and on the parameters
        The URI specifies the measured quantity, while the parameters can be
        used to select a specific sensor.
        """
        if len(uri) == 0:
            # Return all measurements in a single list (flatten list of sublists)
            if 'sens' in params:
                # Need to filter by sensor as well
                try:
                    req_sens_id = int(params['sens'])     # If ok, the parameter is the ID
                except:
                    req_sens = str(params['sens'])
                    req_sens_id = self.getSensID(req_sens)
                
                meas_lst = self.getMeasurements(type=None, sens=req_sens_id)
                return json.dumps(meas_lst)
            else:
                # No sensor specified
                return json.dumps(self.getMeasurements())
            
        elif len(uri) == 1:
            # 'Switch' over measurements
            if (str(uri[0]) in self.all_meas_types):
                if 'sens' in params:
                    # Need to filter by sensor as well
                    try:
                        req_sens_id = int(params['sens'])     # If ok, the parameter is the ID
                    except:
                        req_sens = str(params['sens'])
                        req_sens_id = self.getSensID(req_sens)
                    
                    meas_lst = self.getMeasurements(type=str(uri[0]), sens=req_sens_id)
                else:
                    # No sensor specified
                    meas_lst = self.getMeasurements(type=str(uri[0]))

                return json.dumps(meas_lst)
            
            else:
                raise cherrypy.HTTPError(404, f"Measurement {str(uri[0])} not found!")
            
    ##################################################################
    def getMeasurements(self, type=None, sens=None):
        """
        This method is used to retrieve the measurements stored in self.last_meas.
        The search can be done by measurement type and/or by sensor name. If none 
        is specified, the entire list of sub-lists is flattened and returned.
        The returned value is always a string of dicts, all of which are in SenML
        format.
        ---------------------------------------------------------------------------
        Input parameters:
        - type: (default None) can be a list of strings or a single string, 
        identifying the requested measurement types
        - sens: (default None) can be a list of strings, a single string, a list 
        of integers or a single integer identifying the requested sensors
        ---------------------------------------------------------------------------
        """
        if sens is None:
            # Flatten the whole list
            flat_list = [el for sublist in self.last_meas for el in sublist]
            if type is None:
                return flat_list
            elif isinstance(type, str):
                # One measurement is required
                out_list = []
                for ms in flat_list:
                    if ms["n"].lower().replace(' ', '_') == type:
                        out_list.append(ms)
                return out_list
            elif isinstance(type, list):
                # More htan 1 measurement types are required
                out_list = []
                for ms in flat_list:
                    if ms["n"].lower().replace(' ', '_') in type:
                        out_list.append(ms)
                return out_list
        else:
            ## NOTE: sens can be a list of strings (sensor names) or of integer numbers (IDs)
            # First, isolate sensor measurements by means of self.dev_agent
            if isinstance(sens, str) or isinstance(sens, int):
                sens = [sens]
            
            sel_list = []
            for sn in sens:
                if isinstance(sn, int):
                    # Already have ID
                    curr_id = sn
                else:
                    # Translate name into ID
                    curr_id = self.getSensID(sn)
                # Get corresponding sublist
                curr_meas_sl = self.last_meas[self.dev_agent_ind_sens[str(curr_id)]]
                # 'Append' sublist to the list of selected measurements
                sel_list += curr_meas_sl
            if type is not None:
                # Filter the measurements according to type
                if isinstance(type, str):
                # One measurement is required
                    out_list = []
                    for ms in sel_list:
                        if ms["n"].lower().replace(' ', '_') == type:
                            out_list.append(ms)
                    return out_list
                elif isinstance(type, list):
                    # More htan 1 measurement types are required
                    out_list = []
                    for ms in sel_list:
                        if ms["n"].lower().replace(' ', '_') in type:
                            out_list.append(ms)
                    return out_list
            
            return sel_list


    def getSensID(self, sensName):
        """
        Return the sensor ID given the name
        ---
        If found, the output is the sensor ID. If not, the output is -1.
        """
        for sns in self.whoami["resources"]["sensors"]:
            if sns["device_name"] == sensName:
                return sns["id"]
        
        # If here, sensor was not found
        return -1


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
                for serv_det in act["services_details"]:
                    if "topic" in serv_det.keys():
                        # Find the actuator associated with the specified topic
                        # NOTE: there is one topic per actuator
                        if topic == serv_det["topic"][0]:
                            
                            # Locate the position of the correct device agent in the list
                            # 'dev_agents_act' via the dictionary 'self_agent_ind_act'

                            # Payload may be either 'start' or 'stop' - this method will 
                            # 'blindly' call the associated method on the device agent
                            index = self.dev_agent_ind_act[str(act["id"])]
                            if message["cmd"] == "start":
                                if self.dev_agents_act[index].isOn() == False:
                                    self.dev_agents_act[index].start()
                                    print(f"Actuator {act['id']} was turned on at time {message['t']}")
                                else:
                                    print(f"Tried to turn on actuator {act['id']}, but it was on!")
                            elif message["cmd"] == "stop":
                                if self.dev_agents_act[index].isOn() == True:
                                    self.dev_agents_act[index].stop()
                                    print(f"Actuator {act['id']} was turned off at time {message['t']}")
                                else:
                                    print(f"Tried to turn off actuator {act['id']}, but it was off!")
                    
                    # May need more customization, e.g., turn on for a specified period
                    # but this must be handled by the corresponding strategy


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
            if r.ok:
                self.broker_info = r.json()
                print("Broker info retrieved!")
                return 1
            else:
                print(f"Error {r.status_code} ☀︎")
        
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
        addr = self.sc_addr + "/device_catalog"
        while tries <= max_tries and self.dev_cat_info == {}:
            try:
                r = requests.get(addr)
                if r.ok:
                    self.dev_cat_info = r.json()
                    self.dev_cat_timestamp = time.time()
                    tries += 1
                    time.sleep(3)
                else:
                    print(f"Error {r.status_code} - it was not possible to retrieve the device catalog info")
                    tries += 1
                    time.sleep(3)
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                tries += 1
                time.sleep(3)
        
        if self.dev_cat_info != {}:
            # It may be that the device catalog is not registered, hence the returned 
            # dict is {} anyways
            print("Device catalog info retrieved!")
            print(json.dumps(self.dev_cat_info))
            return 1
        else:
            print("Max. tries exceeded - it was not possible to retrieve the device catalog info")
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


    def registerAtDevCat(self, max_tries=25):
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
            addr_dev_cat = "http://" + self.dev_cat_info["ip"] + ":" + str(self.dev_cat_info["port"])
            
            # Get ID
            if not self._id_assigned:
                id_addr = addr_dev_cat + "/new_id"

                t = 0
                while t <= max_tries and not self._id_assigned:
                    
                    try:
                        r_id = requests.get(id_addr)

                        if r_id.ok:
                            myID = r_id.json()['id']
                            self.whoami['id'] = myID
                            self._id_assigned = True
                            print(f"Received ID {myID}")
                        else:
                            print(f"Error {r_id.status_code} - unable to get ID")
                    except:
                        print("Tried to request ID - failed to establish a connection")
                    
                    time.sleep(3)
            
            addr = addr_dev_cat + "/device"
            while tries <= max_tries and not self._registered_dev_cat:  
                try:
                    r = requests.post(addr, data=json.dumps(self.whoami))
                    if r.ok:
                        # self.dev_cat_info = r.json()
                        self._registered_dev_cat = True
                        print("Registered!")
                    elif r.status_code == 400:
                        print("Device was already registered!\n↓")
                        self._registered_dev_cat = True
                        if self.updateDevCat() == 1:
                            return 1
                        else:
                            print("Unable to update info")
                    else:
                        print(f"Error {r.status_code} - unable to update device information on device catalog")
                    tries += 1
                    time.sleep(3)
                except:
                    print("Tried to register at device catalog - failed to establish a connection!")
                    tries += 1
                    time.sleep(3)
            
            if self._registered_dev_cat:
                # Success
                return 1
            else:
                # Not registered
                return 0
        else: 
            print("Missing device catalog info!")
            return -1


    def updateDevCat(self, max_tries=25):
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
            addr_dev_cat = "http://" + self.dev_cat_info["ip"] + ":" + str(self.dev_cat_info["port"])
            addr = addr_dev_cat + "/device"
            while tries <= max_tries and not upd_succ:
                try:    
                    r = requests.put(addr, data=json.dumps(self.whoami))
                    if r.ok:
                        # self.dev_cat_info = r.json()
                        print("Information updated!")
                        return 1
                    elif r.status_code == 400:  # From dev. cat.: if unable to update, the return code is 400
                        # Try to POST
                        self._registered_dev_cat = False
                        if self.registerAtDevCat() == 1:
                            print("→Had to register!")
                            return 1
                    else:
                        print(f"Error {r.status_code}")
                        tries += 1
                        time.sleep(3)
                except:
                    print("Unable to reach device catalog to update information!")
                    tries += 1
                    time.sleep(3)

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
            print(f"Measuring with sensor {sens_id}")
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
                    warnings.warn(f"Null {curr_meas['n']} measurement at {curr_meas['t']}")
            
            elif isinstance(curr_meas, list):
                self.last_meas[self.dev_agent_ind_sens[sens_id]] = curr_meas

                for meas in curr_meas:
                    if meas["v"] is None:
                        warnings.warn(f"Null {meas['n']} measurement at {meas['t']}")

    
    def publishLastMeas(self):
        # Read all sensor topics from "self.whoami"
        # Find the last measured value for the specific quantity 
        # (use indexing in `self.dev_agent_ind_sens`)
        for sens in self.whoami["resources"]["sensors"]:
            if "MQTT" in sens["available_services"]:
                # Retrieve last measurements via the name-index mapping
                meas_lst = self.last_meas[self.dev_agent_ind_sens[str(sens["id"])]]
                # Find available topics
                for det in sens["services_details"]:
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
                                    # print(f"Published in topic {top_iter}")
        
        # Keep in mind: can use wildcards (at subscriber) to obtain all measurements
        # for a single parameter if it is measured by multiple sensors


    def getIP(self):
        for ed in self.conf["device_connector"]["endpoints_details"]:
            if ed["endpoint"] == "REST":
                return ed["ip"]
    

    def getPort(self):
        for ed in self.conf["device_connector"]["endpoints_details"]:
            if ed["endpoint"] == "REST":
                return ed["port"]
            
    def beginOperation(self):
        
        ###############################################
        # Launch web service
        cherrypy.tree.mount(self, '/', self._http_conf)
        cherrypy.config.update({'server.socket_host': self.getIP()})
        cherrypy.config.update({'server.socket_port': self.getPort()})

        ############### Start operation ###############

        ok = False
        max_iter_init = 10
        iter_init = 0

        try:
            while not ok:
                self.connectToServCat(max_tries=100)
                init_status = self.registerAtDevCat(max_tries=100)

                if init_status == 1:
                    # Correctly registered
                    ok = True
                elif init_status == 0:
                    iter_init += 1
                elif init_status == -1:
                    # No dev. cat. info
                    iter_init += 1
                    self.connectToServCat()

                if iter_init >= max_iter_init:
                    # If too many tries - wait some time, then retry
                    iter_init = 0
                    time.sleep(10)
        except KeyboardInterrupt:
            pass    # May need to disconnect from broker

    def workingLoop(self):
        ############### Working loop ###############
        meas_timeout = 60           # Time for measurement update
        t_last_meas = 0             # This triggers measurements in first loop

        cherrypy.engine.start()

        try:
            while True:
                print("\nlooping . . .")
                # Update info
                upd_oper = self.updateDevCat(max_tries=10)
                
                if upd_oper == -1:
                    # No dev cat info
                    self.connectToServCat()
                    upd_oper = self.updateDevCat()
                
                # No `elif` - upd_oper could have been updated
                if upd_oper == 0:
                    # Cannot reach device catalog
                    warnings.warn("Could not reach device catalog!")
                    
                    # It may be that the device catalog was moved - get new address
                    self.connectToServCat()

                # Make and publish measurements
                curr_time = time.time()
                if curr_time - t_last_meas > meas_timeout:
                    self.updateMeas()
                    self.publishLastMeas()
                    t_last_meas = time.time()
                # Clean possibly old info
                self.cleanupDevCat()

                time.sleep(5)
        except KeyboardInterrupt:
            cherrypy.engine.stop()

###############################################################################
### Main program - include loop

if __name__ == "__main__":
    myDevConn = DevConn("conf_dev_conn.json", "device_info.json", own_ID=True)

    myDevConn.beginOperation()

    myDevConn.workingLoop()