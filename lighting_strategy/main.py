import json
import paho.mqtt.client as PahoMQTT
from sub.MyMQTT import MyMQTT
import requests
import time
import warnings

#

LIGHT_SUNNY = 10000         # Lux
LIGHT_CLOUDY = 1000         # Lux

#
#
#
#
#

class LightingStrategy():

    def __init__(self, conf_path="light_conf.json", out_conf="light_conf_updated.json", own_ID=False):
        self._conf_path = conf_path
        try:
            with open(conf_path) as f:
                self._conf = json.load(f)
        except:
            with open("lighting_strategy/" + conf_path) as f:
                self._conf = json.load(f)

        self._serv_cat_addr = "http://" + self._conf["services_catalog"]["ip"] + ":" + str(self._conf["services_catalog"]["port"])    # Address of services catalog
        self.whoami = self._conf["lighting_strategy"]         # Own information - to be sent to the services catalog

        self._out_conf_path = out_conf

        # NOT DONE, since no web service needs to be launched for this microservice
        # for ed in self.whoami["endpoints_details"]:
        #     if ed["endpoint"] == "REST":
        #         self.ip = ed["address"].split(':')[1].split('//')[1]
        #         self.port = int(ed["address"].split(':')[-1])

        if own_ID:
            self.id = self.whoami["id"]
        else:
            # If the ID was not manually assigned (in the conf), the initial value is set to None
            self.id = None
            self.getServiceID()

        self._registered_at_catalog = False
        self._last_update_serv = 0
        self.registerAtServiceCatalog(max_tries=25)

        ## Get broker information and initialize mqtt client
        self._broker_info = {}           # No timestamp - suppose it does not change
        
        while self._broker_info == {}:
            if self.getBrokerInfo(max_tries=100) != 1:
                print("Cannot get broker info!")
                time.sleep(10)

        # MQTT publisher base name
        for ed in self.whoami["endpoints_details"]:
            if ed["endpoint"] == "MQTT":
                self.mqtt_bn = ed["bn"]

        self.mqtt_cli = MyMQTT(
            clientID=self.mqtt_bn,    # Devices can have same name, but must not have same id
            broker=self._broker_info["ip"],
            port=self._broker_info["port_n"],
            notifier=self
        )
        # List of topics to subscribe to in order to receive lighting info
        # Initially empty
        self.topics_list = []

        # Connect to the broker
        self.mqtt_cli.start()

        self._dev_cat_info = {}
        self.getDevCatInfo()

        # Store info about the devices
        # Only keep the ones which have both the lighting sensor and the 
        # actuator for the lights
        self._devices = []
        
        # Each element of _devices has the same shape:
        # Each of the two elements contains the associated topic
        self._dev_template = {
            "measurement": "",
            "actuator": ""
        }
        
    #####################################################################################

    def notify(self, topic, msg):
        pass

    #####################################################################################

    def getServiceID(self, max_tries=20):
        """
        Request ID from service catalog.

        The method returns 1 if the ID is assigned, else 0
        """
        tries = 0
        serv_cat_id = self._serv_cat_addr + '/new_serv_id'
        while self.id is None and tries < 2*max_tries:
            tries += 1
            try:
                r_id = requests.get(serv_cat_id)
                if r_id.ok:
                    self.id = r_id.json()
                    self.whoami["id"] = self.id
                    with open(self.out_conf, 'w') as f:
                        json.dump(self.whoami, f)
                    return 1
                else:
                    # Should not happen
                    print("Error - unable to get ID from server!")
                    time.sleep(3)
            except:
                print("Unable to reach service catalog to retrieve ID")
                time.sleep(3)

        if self.id is not None:
            print("ID already assigned")
            return 1
        else:
            warnings.warn("It was not possible to retrieve the service ID")
            return 0

    def registerAtServiceCatalog(self, max_tries=10):
        """
        This method is used to register the device catalog information
        on the service catalog.
        -----
        Return values:
        - 1: registration successful
        - -1: information was already present - update was performed
        - 0: failed to add (unreachable server)
        """

        if self.id is None:
            self.getServiceID()

        # Actual
        tries = 0
        while not self._registered_at_catalog and tries < max_tries and self.id is not None:            
            tries += 1
            try:
                reg = requests.post(self._serv_cat_addr + '/service', data=json.dumps(self.whoami))
                print(f"Sent request to {self._serv_cat_addr}")
                
                if reg.status_code == 201:
                    self._registered_at_catalog = True
                    self._last_update_serv = time.time()
                    print("Successfully registered at service catalog!")
                    return 1
                elif reg.status_code == 400:
                    print("Device catalog was already registered!")
                    self._registered_at_catalog = True
                    # Perform an update, to keep the last_update recent
                    self.updateServiceCatalog()
                    return -1
                else:
                    print(f"Status code: {reg.status_code}")
                time.sleep(5)
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                time.sleep(5)

    def updateServiceCatalog(self, max_tries=10):
        """
        This ethod is used to update the information of the device catalog 
        at the services catalog.
        ------
        Return values:
        - 1: update successful
        - -1: needed to register first
        - 0: unable to reach server
        """
        # Try refreshing info (PUT) - code 200
        # If it fails with code 400 -> cannot update
            # Perform POST

        if self.id is None:
            self.getServiceID()

        updated = False
        count_fail = 0

        while not updated and count_fail < max_tries:
            try:
                try1 = requests.put(self._serv_cat_addr + '/service', data=json.dumps(self.whoami))

                # If here, it was possible to send the request to the server (reachable)
                if try1.status_code == 200:
                    # Update successful
                    print("Information in the service catalog was successfully updated!")
                    self._last_update_serv = time.time()
                    return 1
                elif try1.status_code == 400:
                    print("Unable to update information at the service catalog ---> trying to register")
                    count_fail += 1
                    self._registered_at_catalog = False
                    self.registerAtServiceCatalog()
                    if self._registered_at_catalog:
                        updated = True
                        return -1
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                count_fail += 1
                time.sleep(5)
        
        # If here, then it was not possible to update nor register information
        # within the maximum number of iterations, which means it was not possible 
        # to reach the server
        print("Maximum number of tries exceeded - service catalog was unreachable!")
        return 0

    def getBrokerInfo(self, max_tries=50):
        """
        Obtain the broker information from the services catalog.
        ----------------------------------------------------------
        Need to specify the maximum number of tries (default 50).
        ----------------------------------------------------------
        Return values:
        - 1: information was correctly retrieved and is stored in
        attribute self._broker_info
        - 0: the information was not received (for how the 
        services catalog is implemented, it means that it was not
        possible to reach it)
        ----------------------------------------------------------
        Note that the broker information is supposed unchanged
        during the use of the application.
        """
        tries = 0
        while tries <= max_tries and self._broker_info == {}:
            tries += 1
            addr = self._serv_cat_addr + "/broker"
            r = requests.get(addr)
            if r.ok:
                self._broker_info = r.json()
                print("Broker info retrieved!")
                return 1
            else:
                print(f"Error {r.status_code} ☀︎")
        
        if self._broker_info != {}:
            return 1
        else:
            return 0

    def getDevCatInfo(self, max_tries=25):
        """
        Obtain the device catalog information from the services
        catalog.
        ----------------------------------------------------------
        Need to specify the maximum number of tries (default 50).
        ----------------------------------------------------------
        Return values:
        - 1: information was correctly retrieved and is stored in
        attribute self._dev_cat_info
        - 0: the information was not received (for how the 
        services catalog is implemented, it means that it was not
        possible to reach it)
        ----------------------------------------------------------
        """
        tries = 0
        addr = self._serv_cat_addr + "/device_catalog"
        while self._dev_cat_info == {} and tries < max_tries:
            tries += 1
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
        """
        Check age of device catalog information - if old, clean it.

        The max age is 'timeout' (default 120s - 2 min).
        """
        if self._dev_cat_info != {}:
            curr_time = time.time()
            if (curr_time - self._dev_cat_info["last_update"]) > timeout:
                self._dev_cat_info = {}

    def updateDevices(self, max_tries=15):
        # Check device cat info exists:
        if self._dev_cat_info == {}:
            if self.getDevCatInfo() == 0:
                print("Unable to get device catalog info")
                return -1
        
        
        try:
            tries = 0
            dc_addr = "http://" + self._dev_cat_info["ip"] + ":" + str(self._dev_cat_info["port"]) + "/devices"
            while tries < max_tries:
                tries += 1
                try:
                    r = requests.get(dc_addr)
                    
                    if r.ok:
                        dev_list = r.json()

                        # Only keep the ones which have the correct sensor and actuator
                        for d in dev_list:
                            # Look for light sensor
                            sens_ok = False
                            top_s = ""
                            for s in d["resources"]["sensors"]:
                                if "Light Intensity" in s["measure_type"]:
                                    sens_ok = True
                                    if "MQTT" in s["available_services"]:
                                        for ser in s["services_details"]:
                                            if ser["service_type"] == "MQTT":
                                                for top in ser["topic"]:
                                                    if top.endswith("light_intensity"):
                                                        top_s = top

                            # Look for actuator
                            act_ok = False
                            top_a = ""
                            for s in d["resources"]["actuators"]:
                                if "MQTT" in s["available_services"]:
                                    for det in s["services_details"]:
                                        if det["service_type"] == "MQTT":
                                            for top in det["topic"]:
                                                if top.endswith("act_light"):
                                                    act_ok = True
                                                    top_a = top

                            new_info = self._dev_template.copy()
                            new_info["measurement"] = top_s
                            self.mqtt_cli.mySubscribe(top_s)
                            new_info["actuator"] = top_a

                            # TODO

                    else:
                        print("Unable to obtain devices list from device cataolg!")
                        time.sleep(3)
                        



                except:
                    print("Unable to connect to device catalog")
        
        
        
        except:
            print("Unable to contact the device cataolg!")
            time.sleep(3)

if __name__ == "__main__":
    pass
