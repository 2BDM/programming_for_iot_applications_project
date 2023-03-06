import json
import requests
import time
from sub.MyMQTT import MyMQTT

class lighting_strategy:
    
    def __init__(self, conf_file="light_conf.json"): 

        # Importing configuration file
        self._conf_path = conf_file
        try:
            with open(conf_file) as f:
                self._conf = json.load(f)
        except:
            with open("lighting_strategy/" + conf_file) as f: 
                self._conf = json.load(f)
       

        # Creating service catalog address and saving the information to send to the service catalog
        self._serv_cat_address = "http://" + self._conf["services_catalog"]["ip"] + ":" + str(self._conf["services_catalog"]["port"])
        self.whoami = self._conf["lighting_strategy"]
        

        # Connect to the services catalog
        self._registered_at_catalog = False
        self._last_update_serv = 0
        self.registerAtServiceCatalog(max_tries=25)
    

        # Retrieving broker informations from service catalog
        self._broker_info = {}

        while self._broker_info == {}:
            if self.getBrokerInfo(max_tries=100) != 1:
                print("Cannot get broker info!")
                time.sleep(10)


        # MQTT publisher base name
        for ed in self.whoami["endpoints_details"]:
            if ed["endpoint"] == "MQTT":
                self.mqtt_bn = ed["bn"]

        self.mqtt_cli = MyMQTT(
            clientID=self.mqtt_bn,    
            broker=self._broker_info["ip"],
            port=self._broker_info["port_n"],
            notifier=self
        )

        # List of topics to subscribe to as the weather
        self.topics_list = []               # "smartGreenhouse/1/BH1750/light_intensity"
        # List of topics of actuators
        self.topics_actuator_list = []      # "smartGreenhouse/1/act_light"

        # Connect to the broker
        self.mqtt_cli.start()


        self.greenhouses = []
        self._last_update_gh = 0
        self._dev_cat_info = {}

        self._devices = {
            "list": [],
            "last_update": 0
        }


    # Mi serve??
    def stop(self):
        self.mqtt_cli.stop()



    def notify(self, topic, payload):
        print(f"Received message in {topic}")
        message = json.loads(payload)
        #Extracting the value of the sensor
        light_value = message["e"][0]["v"]

        #plant_type = None
        #max_light_lux = None
        min_light_lux = None

        for gh in self.greenhouses:
            if gh["device_id"] == topic.split("/")[1]: #Same device_id
                #plant_type = gh["plant_type"]
                for need in gh["plant_needs"]:
                    keys = need.keys()
                    if "min_light_lux" in keys:
                        min_light_lux = need["min_light_lux"]
                    '''
                    if "max_light_lux" in keys:
                        max_light_lux = need["max_light_lux"]
                    '''

        if light_value >= min_light_lux:
            topic = self.topics_actuator_list[0]
            message = {
                "cmd": "stop",
                "t": time.time()
            }
            self.mqtt_cli.myPublish(topic, message)

        else: #light_value < min_light_lux
            topic = self.topics_actuator_list[0]
            message = {
                "cmd": "start",
                "t": time.time()
            }
            self.mqtt_cli.myPublish(topic, message)


    def getGreenhouses(self, max_tries=25): 
        tries = 0
        while tries < max_tries and self.greenhouses == []:
            tries += 1
            try:
                req = requests.get(self._serv_cat_address + "/greenhouses")
                if req.ok:
                    self.greenhouses = req.json()
                    self._last_update_gh = time.time()
                    print("Greenhouses info retrieved!")
                    return 1
                else:
                    print(f"Error {req.status_code}")
                    time.sleep(5)
            except:
                print("Unable to reach service catalog - retrying")
                time.sleep(5)
        
        if self.greenhouses != []:
            return 1
        else:
            return 0


    def registerAtServiceCatalog(self, max_tries = 10):
        tries = 0

        addr = self._serv_cat_address + "/service"
        while not self._registered_at_catalog and tries < max_tries:
            tries += 1
            try:
                reg = requests.post(addr, data = json.dumps(self.whoami))
                print(f"Sent request to {self._serv_cat_address}")

                if reg.status_code == 201:
                    self._registered_at_catalog = True
                    self._last_update_serv = time.time()
                    print("Successfully registered at service catalog!")
                    return 1
                elif reg.status_code == 400:
                    print("Was already registered!")
                    self._registered_at_catalog = True
                    # Perform an update, to keep the last_update recent
                    self.updateServiceCatalog()
                    return -1
                else:
                    print(f"Status code: {reg.status_code}")
                time.sleep(5)

            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                tries += 1
                time.sleep(5)


    def updateServiceCatalog(self, max_tries = 10):
        updated = False
        count_fail = 0
        tries = 0
        while not updated and count_fail < max_tries:
            tries += 1
            try:
                update = requests.put(self._serv_cat_address + '/service', data=json.dumps(self.whoami))

                if update.status_code == 200:
                    print("Information in the service catalog was successfully updated!")
                    self._last_update_serv = time.time()
                    return 1
                elif update.status_code == 400:
                    print("Unable to update information at the service catalog ---> trying to register")
                    count_fail += 1
                    self._registered_at_catalog = False
                    self.registerAtServiceCatalog()
                    if self._registered_at_catalog:
                        updated = True
                        return -1
                
            except:
                print("Tried to connect to services catalog - failed to establish a connection! (2)")
                count_fail += 1
                time.sleep(5)

        print("Maximum number of tries exceeded - service catalog was unreachable!")
        return 0
   

    def getBrokerInfo(self, max_tries = 50):
        tries = 0

        while tries <= max_tries and self._broker_info == {}:
            addr = self._serv_cat_address + "/broker"
            r = requests.get(addr)
            if r.ok:                                   
                self._broker_info = r.json()
                print("Broker info retrieved!")
                return 1
            else:
                print(f"Error {r.status_code}")
        
        if self._broker_info != {}:
            return 1
        else:
            return 0

    
    def getDevCatInfo(self, max_tries=25):
        tries = 0
        while self._dev_cat_info == {} and tries < max_tries:
            addr = self._serv_cat_address + "/device_catalog"
            try:
                r = requests.get(addr)
                if r.ok:
                    self._dev_cat_info = r.json()
                    self._dev_cat_info["last_update"] = time.time()
                    print("Device catalog info retrieved!")
                    return 1
                else:
                    print(f"Error {r.status_code}")
                    time.sleep(5)
            except:
                print("Unable to reach services catalog - retrying")
                time.sleep(5)
        
        if self._dev_cat_info != {}:
            return 1
        else:
            return 0


    def cleanupDevCatInfo(self, timeout=120):
        
        if self._dev_cat_info != {}:
            curr_time = time.time()
            if (curr_time - self._dev_cat_info["last_update"]) > timeout:
                self._dev_cat_info = {}

    def cleanupGreenhouses(self, timeout=120):
        
        if self.greenhouses != {}:
            curr_time = time.time()
            if (curr_time - self._last_update_gh) > timeout:
                self.greenhouses = []


    def getListOfDevices(self, max_tries=25, info_timeout=120):
        
        # Check device cat info exists:
        if self._dev_cat_info == {}:
            if self.getDevCatInfo() == 0:
                print("Unable to get device catalog info")
                return -1  
    
        tries = 0
        try:
            dc_addr = "http://" + self._dev_cat_info["ip"] + ":" + str(self._dev_cat_info["port"]) + "/devices"
            while tries < max_tries:
                try:
                    r = requests.get(dc_addr)
                    if r.ok:
                        # The response is the list
                        self._devices["list"] = r.json()
                        self._devices["last_update"] = time.time()
                        print("Obtained updated devices list")
                        return 1
                    else:
                        print(f"Error {r.status_code}")
                        time.sleep(5)
                except:
                    print("Unable to reach device catalog!")
                    time.sleep(5)
            
            print("Unable to retrieve devices list")
        except:
            print("No device catalog found at services catalog!")
        return 0

    def clearDevicesList(self, info_timeout=120):
        
        if (time.time() - self._devices["last_update"]) > info_timeout:
            self._devices = {
                "list": [],
                "last_update": 0
            }
            return 1
        return 0

    def subscribeToTopics(self, info_timeout=120):

        # First, check the devices list is empty or outdated
        if self._devices["list"] == [] or (time.time() - self._devices["last_update"]) > info_timeout:
            # Attempt to retrieve info
            self.getListOfDevices()

        if self._devices["list"] != []:
            
            n_sub = 0
            for dev in self._devices["list"]:                   
                for sens in dev["resources"]["sensors"]:        
                    if "MQTT" in sens["available_services"]:    
                        for det in sens["services_details"]:   
                            if det["service_type"] == "MQTT":   
                                for top in det["topic"]:        
                                    if top.split('/')[-1] == "light_intensity" and top not in self.topics_list:
                                        # Sub to the topic
                                        self.mqtt_cli.mySubscribe(top)
                                        # Add topic to the list
                                        self.topics_list.append(top)
                                        n_sub += 1
            
            return n_sub
    
    def retrieveActuatorTopic(self, info_timeout=120):

        # First, check the devices list is empty or outdated
        if self._devices["list"] == [] or (time.time() - self._devices["last_update"]) > info_timeout:
            # Attempt to retrieve info
            self.getListOfDevices()

        if self._devices["list"] != []:
            
            n_sub = 0
            for dev in self._devices["list"]:                   
                for sens in dev["resources"]["actuators"]:        
                    if "MQTT" in sens["available_services"]:    
                        for det in sens["services_details"]:   
                            if det["service_type"] == "MQTT":   
                                for top in det["topic"]:        
                                    if top.split('/')[-1] == "act_light" and top not in self.topics_actuator_list:
                                        # Add topic to the list
                                        self.topics_actuator_list.append(top)
                                        n_sub += 1
            
            return n_sub


    def mainLoop(self):

        while True:
            time.sleep(5)

            self.getGreenhouses()
            self.updateServiceCatalog()

            self.getDevCatInfo()
            self.getListOfDevices()

            self.subscribeToTopics()

            self.cleanupDevCatInfo()
            self.cleanupGreenhouses()
            self.clearDevicesList()





if __name__ == "__main__":
    light_str = lighting_strategy()
    try:
        light_str.mainLoop()
    except KeyboardInterrupt:
        print("Program stopped")
        light_str.stop()
