import json
import paho.mqtt.client as PahoMQTT
from sub.MyMQTT import MyMQTT
import requests
import time
import warnings
import sys

""" 
Water delivery strategy
"""

MOIST_LOW = 10      # %
WEIGHT_LOW = 50     # g
#
#
#
#
#

class WaterDeliveryStrategy():

    def __init__(self, conf_path="water_conf.json", out_conf="water_conf_updated.json", own_ID=False):
        self._conf_path = conf_path
        try:
            with open(conf_path) as f:
                self._conf = json.load(f)
        except:
            with open("water_delivery_strategy/" + conf_path) as f:
                self._conf = json.load(f)

        self._serv_cat_addr = "http://" + self._conf["services_catalog"]["ip"] + ":" + str(self._conf["services_catalog"]["port"])    # Address of services catalog
        self.whoami = self._conf["water_delivery"]         # Own information - to be sent to the services catalog

        self._out_conf_path = out_conf

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

        # Get Telegram bot info
        self._telegram_bot_info = {}
        self.getTelegramInfo()

        # Store info about the devices
        # Only keep the ones which have both the lighting sensor and the 
        # actuator for the lights
        self._devices = []
        
        # Each element of _devices has the same shape:
        # Each of the first two elements contains the associated topic
        # 'tank' contains the (non-compulsory) tank weight topic
        # 'last_3' counts for how many subsequent times the measurement was 
        # below threshold (...) and possibly triggers the actuation
        # 'curr_state' contains the current actuator state
        # 'min_moist' is the lower bound for the moisture, for the specific plant
        # '--> this is the value used as threshold
        self._dev_template = {
            "measurement": "",
            "actuator": "",
            "tank": "",
            "last_3": 0,
            "curr_state": "off",
            "min_moist": 0,
            "last_tank_notif": 0,
            "timestamp": 0
        }

        self._tank_notif_timeout = 12*3600      # 12 hours
        
    #####################################################################################

    def notify(self, topic, msg):
        """
        ## notify

        Callback for MyMQTT object.
        ---
        As a message (containing the measurement) is received, the topic is searched 
        in self._devices.
        Then, depending on the current_state and on the measurement value, it is decided
        whether to activate the light or not.

        Activation happens if for 5 consecutive measurements the light intensity value is 
        below the minimum value. The artificial light is turned off if the 
        light intensity value is above the threshold for 5 times.
        ---
        Return values:
        - 1: irrigation was triggered
        - 0: error - unable to locate device info
        """
        max_tries = 10

        # First, iterate over self._devices to find the topic associated with the 
        # received message
        for dv in self._devices:
            if dv["measurement"] == topic:
                # Extract measurement (SenML)
                # Check:
                assert (msg['e'][0]['u'] == 'Lux'), f"Unit is actually {msg['e'][0]['u']}"

                low_thresh = dv["min_moist"]

                if msg['e'][0]['u'] == 'Lux':
                    meas = msg['e'][0]['v']
                else:
                    # May receive other units from different sensors
                    # Here, one should call methods to convert the units

                    # Not implemented
                    pass

                if meas <= low_thresh:
                    if dv["curr_state"] == "off":
                        dv["last_3"] += 1
                else:
                    dv["last_3"] = 0

                # (At least) 3 meas lower than the threshold trigger 
                # the irrigation
                # As long as the value keeps on being lower, the 
                # irrigation will be triggered at each measurement
                if dv["last_3"] >= 3:
                    # Trigger watering
                    # MQTT message for actuator:
                    msg_on = {
                        "cmd": "on",
                        "t": time.time()
                    }
                    msg_off = {
                        "cmd": "off",
                        "t": time.time()
                    }

                    self.mqtt_cli.myPublish(dv["actuator"], msg_on)
                    time.sleep(10)
                    self.mqtt_cli.myPublish(dv["actuator"], msg_off)

                    # If there is no tank topic, get info via REST
                    # If the topic is present, this is done when 
                    # the measurement is received via the topic
                    if dv["tank"] == "":
                        dev_id = dv["measurement"].split('/')[1]

                        # Get device info:
                        self.cleanupDevCatInfo()
                        self.getDevCatInfo()

                        if self._dev_cat_info != {}:
                            this_dev = {}
                            tries = 0
                            addr = 'http://' + self._dev_cat_info["ip"] + ':' + str(self._dev_cat_info["port"]) + '/device?id=' + str(dev_id)
                            while this_dev == {} and tries < max_tries:
                                tries += 1
                                try:
                                    r = requests.get(addr)
                                    if r.ok:
                                        this_dev = r.json()
                                    else:
                                        print(f"Error {r.status_code} - unable to get device {dev_id} information!")
                                        time.sleep(3)
                                except:
                                    print(f"Unable to reach device catalog!")
                                    time.sleep(3)
                            
                            uri_tank = ""
                            if this_dev != {}:
                                for sens in this_dev["resources"]["sensors"]:
                                    if sens["measure_type"] == "Tank Weight" and "MQTT" not in sens["available_services"]:
                                        for sd in sens["services_details"]:
                                            if sd["service_type"] == "REST":
                                                uri_tank = sd["uri"]

                            if uri_tank != "":
                                tries = 0
                                wt = {}
                                while tries < max_tries and wt == {}:
                                    try:
                                        r2 = requests.get(uri_tank)
                                        if r2.ok:
                                            wt = r2.json()
                                        else:
                                            print(f"Error {r2.status_code} - unable to get tank weight from device {dev_id}")
                                            time.sleep(3)
                                    except:
                                        print(f"Unable to reach device connector {dev_id}")
                                        time.sleep(3)
                                
                                if wt != {}:
                                    return self.sendTankNotif(wt, dv)

                            else:
                                print("It was not possible to get the URI for the tank!")
                                return 0
                        else:
                            print("It was not possible to retrieve the device catalog info!")
                            return 0


                return 1
            
            elif dv["tank"] == topic:
                # Trigger message transmission to Telegram 
                return self.sendTankNotif(msg, dv)
          
        print("Error - unable to locate device info")
        return 0

    #####################################################################################

    def getServiceID(self, max_tries=20):
        """
        Request ID from service catalog.

        The method returns 1 if the ID is assigned, else 0. 
        It also updates the configuration by adding the received ID.
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
        This method is used to register the water delivery strategy
        information on the service catalog.
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
        This method is used to update the information of the device catalog 
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

    def getTelegramInfo(self, max_tries=10):
        """
        Obtain the telegram bot information from the services
        catalog.
        ----------------------------------------------------------
        Need to specify the maximum number of tries (default 50).
        ----------------------------------------------------------
        Return values:
        - 1: information was correctly retrieved
        - 0: the information was not received (for how the 
        services catalog is implemented, it means that it was not
        possible to reach it)
        ----------------------------------------------------------
        """
        tries = 0
        addr = self._serv_cat_addr + "/service?name=telegramBot"
        while self._telegram_bot_info == {} and tries < max_tries:
            tries += 1
            try:
                r = requests.get(addr)
                if r.ok:
                    self._telegram_bot_info = r.json()
                    self._telegram_bot_info["last_update"] = time.time()
                    print("Telegram bot info retrieved!")
                    return 1
                else:
                    print(f"Error {r.status_code} - could not get telegram info")
                    time.sleep(5)
            except:
                print("Unable to reach services catalog - retrying")
                time.sleep(5)
        
        if self._telegram_bot_info != {}:
            return 1
        else:
            return 0

    def cleanupTelegramBot(self, timeout=120):
        """
        Check age of Telegram bot information - if old, clean it.

        The max age is 'timeout' (default 120s - 2 min).
        """
        if self._telegram_bot_info != {}:
            curr_time = time.time()
            if (curr_time - self._telegram_bot_info["last_update"]) > timeout:
                self._telegram_bot_info = {}

    def updateDevices(self, max_tries=15):
        """
        This method is used to get the latest information about the devices connected to the device catalog.
        
        As the information is obtained, the water strategy will save only the ones which possess both the
        moisture sensor and an actuator used to control the water.
        Then, it will store the sensor topic and the actuator one in attribute self._devices (following 
        the template in self._dev_template) and subscribe to the sensor topic (after checking it was not 
        already subscribed).

        If available, the program also stores and subscribes to the tank weight topic.

        The parameter 'max_tries' is used to limit the number of requests made to the device catalog for
        getting the devices information.
        """
        
        # Check device cat info exists:
        if self._dev_cat_info == {}:
            if self.getDevCatInfo() == 0:
                print("Unable to get device catalog info")
                return -1
        
        if self._dev_cat_info != {}:
            # If here, the device info is not empty
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
                                if "Soil Moisture" in s["measure_type"]:
                                    if "MQTT" in s["available_services"]:
                                        for ser in s["services_details"]:
                                            if ser["service_type"] == "MQTT":
                                                for top in ser["topic"]:
                                                    if top.endswith("soil_moisture"):
                                                        sens_ok = True
                                                        top_s = top

                            # Look for tank (not compulsory)
                            tank_ok = False
                            top_tank = ""
                            for s in d["resources"]["sensors"]:
                                if "Tank Weight" in s["measure_type"]:
                                    if "MQTT" in s["available_services"]:
                                        for ser in s["services_details"]:
                                            if ser["service_type"] == "MQTT":
                                                for top in ser["topic"]:
                                                    if top.endswith("tank_weight"):
                                                        tank_ok = True
                                                        top_tank = top

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

                            # If both have been found, add the topics to self._devices:
                            if sens_ok and act_ok:
                                new_elem = self._dev_template.copy()
                                # Find the needs, among which there is the 'min_soil_moist' field
                                # Need to request the greenhouse info associated with the current device
                                # NOTE: Greenhouse id == device id (!)
                                addr_gh = self._serv_cat_addr + '/greenhouse?id=' + str(d["id"])
                                
                                tries_2 = 0
                                gh_info = {}
                                while tries_2 < max_tries and gh_info == {}:
                                    try:
                                        r_2 = requests.get(addr_gh)
                                        if r_2.ok:
                                            gh_info = r.json()
                                            # Suppose needs don't change in time - reasonable
                                            print("Plant info retrieved!")
                                        else:
                                            print(f"Error {r_2.status_code} - unable to get greenhouse information")
                                            time.sleep(5)
                                    except:
                                        print("Error - unable to reach services catalog to get greenhouse information")
                                
                                if gh_info != {}:
                                    # Assign needs          %
                                    new_elem["min_moist"] = gh_info["plant_needs"]["min_soil_moist"]

                                
                                new_elem["measurement"] = top_s
                                new_elem["actuator"] = top_a

                                if top_a not in self.topics_list:
                                    # If a new topic for the light sensor is found, 
                                    self.mqtt_cli.mySubscribe(top_a)
                                    self.topics_list.append(top_a)

                                if tank_ok:
                                    # Add tank info
                                    # In our case, the test device only allows the communication via REST
                                    new_elem["tank"] = top_tank
                                    if top_tank not in self.topics_list:
                                        self.mqtt_cli.mySubscribe(top_tank)
                                        self.topics_list.append(top_tank)


                                self._devices.append(new_elem)


                    else:
                        print("Unable to obtain devices list from device cataolg!")
                        time.sleep(3)
                        
                except:
                    print("Unable to connect to device catalog")
                    time.sleep(3)
        else:
            print("Empty device catalog info coming from services catalog!")
            
    def sendTankNotif(self, senml, dev_dict, max_tries=15):
        """
        Send the notification to the user for the tank being empty

        Input parameters:
        - senml: SenML-formatted JSON retrieved from the weighting sensor
        - dev_dict: record in self._devices associated to that device
        - max_tries: maximum number of rest requests before failure
        """
        weight = senml['e'][0]['v']

        # Default unit is grams
        unit = senml['e'][0]['u']

        if unit == 'kg':
            weight = weight*1000
        
        # The message can be sent only if the weight is below the threshold and it has elapsed
        # at least 12 h from the last message (In order not to overwhelm user)
        if weight <= WEIGHT_LOW and (time.time() - dev_dict["last_tank_notif"]) > self._tank_notif_timeout:
            # Recover the weather (if possible!)
            
            self.cleanupTelegramBot()
            self.getTelegramInfo()

            # Update the timeout for the notification
            # Prevent multiple messages to the receiver in low time
            dev_dict["last_tank_notif"] = time.time()

            # Get info about the weather station endpoints:
            tries = 0
            weather_station_addr = ""
            while tries < max_tries and weather_station_addr == "":
                tries += 1

                try:
                    r = requests.get(self._serv_cat_addr + "/service?name=weather_station")
                    
                    if r.ok:
                        weather_station_info = r.json()

                        for det in weather_station_info["endpoints_details"]:
                            if det["endpoint"] == "REST":
                                weather_station_addr = det["address"]
                    else:
                        print(f"Error {r.status_code} - unable to get weather station information!")
                        time.sleep(3)
                except:
                    print(f"Unable to reach services catalog!")
                    time.sleep(3)
            
            if weather_station_addr == "":
                print("It was not possible to obtain weather station info")
                
                # Even if the weather station cannot be reached, send the notification
                dev_id = dev_dict["tank"].split('/')[1]
                
                tries = 0
                addr_tg = ""
                for ed in self._telegram_bot_info["endpoints_details"]:
                    if ed["endpoint"] == "REST":
                        addr_tg = 'http://' + ed["ip"] + ':' + str(ed["port"]) + '/?greenhouseID=' + str(dev_id) + '&required=yes'
                
                if addr_tg != "":
                    while tries < max_tries:
                        tries += 1
                        try:
                            r2 = requests.post(addr_tg)
                            if r2.ok:
                                print("Message sent to user!")
                                return 1
                            else:
                                print(f"Error {r2.status_code} - unable to send post request to telegram bot")
                                time.sleep(3)
                        except:
                            print("Unable to reach Telegram Bot!")
                            time.sleep(3)
                else:
                    print("Unable to retrieve telegram bot address")
                return 0
            else:
                # Can use the weather station to ask for future weather!
                print("Something else")
                # Who takes care of checking future weather??
                dev_id = dev_dict["tank"].split('/')[1]
                # Contact the weather station
                # /will_it_rain?id=

                tries = 0
                will_it_rain = ""
                addr_w = weather_station_addr + '/will_it_rain?id=' + str(dev_id)
                while tries < max_tries and will_it_rain == "":
                    tries += 1
                    try:
                        r_w = requests.get(addr_w)

                        if r_w.ok:         # If the response was correctly received from the weather station
                            resp = r_w.text

                            assert (resp == "yes" or resp == "no"), print(f"The response from the weather station is: {resp}")

                            # Get the telegram bot address:
                            addr_tg = ""
                            for ed in self._telegram_bot_info["endpoints_details"]:
                                if ed["endpoint"] == "REST":
                                    addr_tg = 'http://' + ed["ip"] + ':' + str(ed["port"]) + '/?greenhouseID=' + str(dev_id)

                            #
                            if resp == 'yes':
                                resp_addr = addr_tg + "&required=no"
                            elif resp == 'no':
                                resp_addr = addr_tg + "&required=yes"

                            tries_2 = 0
                            if resp_addr != "":
                                while tries_2 < max_tries:
                                    tries_2 += 1
                                    try:
                                        r2 = requests.post(resp_addr)
                                        if r2.ok:
                                            print("Message sent to user!")
                                            return 1
                                        else:
                                            print(f"Error {r2.status_code} - unable to send post request to telegram bot")
                                            time.sleep(3)
                                    except:
                                        print("Unable to reach Telegram Bot!")
                                        time.sleep(3)
                            else:
                                print("Unable to retrieve telegram bot address")
                            return 0

                        else: 
                            print(f"Error {r_w.status_code} - Unable to get weather forecast from weather station!")
                            time.sleep(3)
                    except:
                        print("Unable to reach weather station!")
                        time.sleep(3)

                return 0
                
    def mainLoop(self, refresh_rate=5):
        while True:
            self.updateDevices()
            self.updateServiceCatalog()
            self.cleanupDevCatInfo()
            self.cleanupTelegramBot()

            self.updateDevices()

            time.sleep(refresh_rate)

if __name__ == "__main__":
    water_delivery = WaterDeliveryStrategy("water_conf.json", "water_conf_updated.json", own_ID=True)

    try:
        water_delivery.mainLoop()
    except KeyboardInterrupt:
        sys.exit(0)