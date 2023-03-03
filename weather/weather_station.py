import cherrypy
import json
import time
import pandas as pd
from datetime import datetime, timedelta
import sys
from sub.MyMQTT import MyMQTT
import requests
import warnings
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
import pickle
import traceback

from weather_predict import COLS_CURRENT, COLS_FUTURE
from weather_predict import currWeather_2, futureRain_2

"""
This is the main program for the weather station.

Functions:
- Connection and subscription to the services catalog
- Retrieval of devices information from the device catalog
- Subscription to sensors topics to obtain measurements (MQTT)
- REST to provide current weather and precipitation forecast
- Ability to send http requests to publish daily weather reports
"""

# GLOBAL VARIABLES - USED FOR MONTH -> SEASON AND SEASON -> ID
SEASON2ID = {
    'winter': 0,
    'spring': 1,
    'summer': 2,
    'fall': 3
}

MONTH2SEASON = {
    '1': 'winter',
    '2': 'winter',
    '3': 'spring',
    '4': 'spring',
    '5': 'spring',
    '6': 'summer',
    '7': 'summer',
    '8': 'summer',
    '9': 'fall',
    '10': 'fall',
    '11': 'fall',
    '12': 'winter'
}

# Lower bounds for light intensity
LIGHT_SUNNY = 10000         # Lux
LIGHT_CLOUDY = 1000         # Lux

def datetime2monthNumber(dt):
    return int(dt.strftime("%m"))

def bar2mb_sealevel(val_bar):
    """
    (Trivial) conversion from bar to millibar w.r.t. sea level atmospheric pressure.
    Needed because the measurements from the pressure sensor are in bar, 
    but the training data for weather prediction is in mb, relative to sea level.
    """
    return (1000*float(val_bar)) - 1013.25

##########################################################################################################

class WeatherStation():

    def __init__(self):
        self.meas_timeout = 24*60*60        # Timeout for forgetting the measurements, in seconds (24 h)
        self.execution_time = "22:00"
        self.current_datetime = datetime.now()                          # !!! datetime object
        self.current_timestamp = time.mktime(self.current_datetime.timetuple())
        self.current_time = self.current_datetime.strftime("%H:%M")     # String
        self.current_date = self.current_datetime.strftime("%Y-%m-%d")  # String (compliant with timestamps)
        self.current_season = MONTH2SEASON[str(datetime2monthNumber(self.current_datetime))]    # String


        # Relevant measurements: the ones for which measurements are needed
        self.relevant_meas_short = [
            "temperature",
            "humidity",
            "pressure",
            "light_intensity"
        ]

        self.relevant_meas = {
            "Temperature",
            "Humidity",
            "Pressure",
            "Light Intensity"
        }

        # Idea: it must contain measurements relative to the lst 24 hours, which are then updloaded to 
        # MongoDB every [HOW MANY?] hours

        # SenML syntax:
        #     {'n': name_of_meas, 'u': units, 't': timestamp, 'v': value}
        # MQTT message syntax:
        #     {'bn': 'base_name', 'e': {'n': name_of_meas, 'u': units, 't': timestamp, 'v': value}}

        """
        devices_meas is the main variable in which the measurements are stored.
        It is a dict, containing as keys the IDs of the devices

        Structure:
        {
            '1': {
                'Temperature': [{'v', 'u', 't'}, {}, ...],

            }
        }

        NOTE: the measurement names are in 'long' format (uppercases and spaces) - as in the SenML messages
        """
        self.devices_meas = {}

    def updateTime(self):
        """
        Automatically update current time, date and season
        """
        self.current_datetime = datetime.now()
        self.current_timestamp = time.mktime(self.current_datetime.timetuple())
        self.current_time = self.current_datetime.strftime("%H:%M")
        self.current_date = self.current_datetime.strftime("%Y-%m-%d")
        self.current_season = MONTH2SEASON[str(datetime2monthNumber(self.current_datetime))]

    def addMeasurement(self, newSenML, dev_id=None):
        """
        Add a new measurement in the local list of measurements.
        ---
        newSenML is the senML-compliant message directly obtained via MQTT 
        (payload) - the device ID must be specified by the user (look at the topic of the rx message).
    
        If not specified, the device ID is inferred from the base name in the senML message.
        
        If the insertion is successful, the return value is 1, else it is 0
        (meaning the attempt generated a python error).
        """
        # First, need to check whether the measurement belongs to the ones 
        # needed - do we? We should only subscribe to topics of useful measurements

        if dev_id is None:
            try:
                id = newSenML["bn"].split('_')[-1]
                warnings.warn("Had to recover device ID for inserting measurement!")
            except:
                raise ValueError("Unable to recover device ID from received message!")
        else:
            id = str(dev_id)

        #try:
        meas_type = newSenML['e'][0]['n']
        
        meas = {            # To be appended in dict
            'v': newSenML['e'][0]['v'],
            'u': newSenML['e'][0]['u'],
            't': newSenML['e'][0]['t']
        }

        # Insert meas:
        if id not in self.devices_meas.keys():
            self.devices_meas[id] = {}
            self.devices_meas[id][meas_type] = []
        else:
            if meas_type not in self.devices_meas[id].keys():
                self.devices_meas[id][meas_type] = []
        
        self.devices_meas[id][meas_type].append(meas)

        return 1
        #except:
            # Hopefully never...
         #   return 0

    def cleanupMeas(self):
        """
        Used to remove old measurements.
        First, the current time is found, then it is used to find (and remove) the old measurements.
        The operation is done for each device, for each measurement.

        NOTE: it must be efficient (since elements are appended as they arrive, if we start 
        cleaning from the first, oldest measurement, as we encounter one element which is not to 
        be removed we can stop the process)

        Return value: number of deleted records
        """
        self.updateTime()

        ts = self.current_timestamp
        to = self.meas_timeout

        n_del = 0

        for id in self.devices_meas.keys():
            for n in self.devices_meas[id].keys():
                # Iterate over the list
                stop = False
                i = 0
                while i < len(self.devices_meas[id][n]) and stop == False:
                    ## TODO: test this - pointers should do the job
                    
                    # NOTE: the index is actually always 0, since we remove from the 1st element
                    # It is needed in the case the list is completely emptied
                    if (ts - self.devices_meas[id][n][i]['t']) > to:
                        # Old --> remove it
                        self.devices_meas[id][n].pop(i)
                        n_del += 1
                    else:
                        stop = True

        return n_del

    def evalMeasPrediction(self, time_range, dev_id):
        """
        Used to evaluate the measurements for the prediction strategy.
        It also adds the season using the current date.
        ---
        The parameter 'time_range' is used to only consider a specific time period to 
        get the measurements from (e.g., 4 hours). It is in seconds.
        ---
        This method is not (typically) called directly, rather it is called by 
        estCurrWeather or estFutureWeather.
        ---
        Measurements for weather:
        - Average temp (cel)
        - Min temp (cel)
        - Max temp (cel)
        - Humidity (%)
        - Pressure (mb relative to sea level) --> Use conversion method (bar2mb_sealevel)
        """
        self.updateTime()

        id = str(dev_id)

        my_meas = self.relevant_meas.copy()
        my_meas.remove("Light Intensity")

        # taken_cat contains the measurements which are to be used
        # Keys are the measurements names
        taken_cat = {}
        for n in my_meas:
            taken_cat[n] = []

        # Get the measurements from the dict
        for n in my_meas:
            for meas in self.devices_meas[id][n]:
                if (self.current_timestamp - meas['t']) <= time_range:
                    # Keep measurement
                    if n == "Air Pressure" and meas['u'] == "Bar":
                        # Need to obtain the barometric pressure in mb 
                        # relative to sea level
                        taken_meas = bar2mb_sealevel(meas['v'])
                    else:
                        taken_meas = float(meas['v'])

                    taken_cat[n].append(taken_meas)
        
        # Evaluate actual values:

        # Mean, min, max temperature:
        t_mean = sum(taken_cat["Temperature"])/len(taken_cat["Temperature"])
        t_min = min(taken_cat["Temperature"])
        t_max = max(taken_cat["Temperature"])

        # Mean humidity:
        h_mean = sum(taken_cat["Humidity"])/len(taken_cat["Humidity"])

        # Mean pressure:
        p_mean = sum(taken_cat["Pressure"])/len(taken_cat["Pressure"])

        # Season:
        seas = MONTH2SEASON[str(datetime2monthNumber(self.current_datetime))]
        seas_id = SEASON2ID[seas]

        out = pd.Series([t_mean, t_min, t_max, h_mean, p_mean, seas_id], index=COLS_CURRENT)

        for k, v in out.items():
            # print(f"------> k = {k}, v = {v}")
            assert (v is not None), f"k = {k}, v = {v}"    
            assert (isinstance(v, float)), f"k = {k}, v = {v}"    
        assert (not out.isnull().values.any()), "NaN in out (evalMeasPrediction)"
        
        return out

    def estCurrWeather(self, device_id=None, time_range=7200, test_el=None, model=None, model_path="models/weather_today.sav"):
        """
        Estimate the current weather from data obtained by the sensors.
        The considered data is given by the maximum age of specified in
        time_range.
        The method 'validates' the result with the use of the light sensor, 
        but only if the prediction is done at daytime.
        ---
        Input parameters:
        - device_id (int): id of the device whose measurements have to be used
        - time_range (int, default 7200): maximum age of the considered data - in s
        - test_el (pd.Series, default None): optional input data alreafy evaluated.
        - model (sklearn model, fitted, default None): optional model to be used,
        must be already trained
        - model_path (default models/weather_today.sav): path specifying the model 
        (.sav file that can be opened with pickle)

        Note: the input data must be formatted having the following columns:
            'TMEDIA °C', 
            'TMIN °C', 
            'TMAX °C', 
            'UMIDITA %', 
            'PRESSIONESLM mb', 
            'STAGIONE'
        ---
        Output values:
        - 1, 'day': rain, tested with light intensity
        - 0, 'day': sunny, tested with light intensity
        - -1, 'day': cloudy, tested with light intensity
        - 1, 'night'
        - 0, 'night'
        - None, '': ERROR
        """
        # The sklearn model is used to estimate the presence of rain. This 
        # estimate is then compared with the measurements about the light 
        # intensity of today, hence it is also possible to estimate the 
        # weather as simply 'cloudy'
        # Alternatives: sunny, cloudy, rainy

        self.updateTime()

        if device_id is None:
            if len(self.devices_meas) > 0:
                # Find 'first' device for which ALL the measurements lists are not empty
                # This prevents to choose devices which may have disconnected
                i = 0
                ok = False
                while i < len(self.devices_meas) and not ok:
                    k = list(self.devices_meas.keys())[i]
                    i += 1
                    ok = True
                    for m in self.devices_meas[k].keys():
                        if self.devices_meas[k][m] == []:
                            ok = False
                
                if i <= len(self.devices_meas):
                    device_id = k            
                else:
                    print("Unable to get measurements - no complete set!")
            else:
                print("No available measurements to be used!")
                return None, ''

        if test_el is None:
            try:
                test_el = self.evalMeasPrediction(time_range, device_id)
            except:
                print("Unable to get measurements!")
                return None, ''

        if model is None:
            # Extract model:
            with open(model_path, 'rb') as f:
                load_model = pickle.load(f)
        else:
            load_model = model
        
        # Perform prediction: 1 if rain/precipitation, else 0
        pred_weather = currWeather_2(test_el, load_model)           # Series object

        # Illumination ranges are defined as global variables
        
        # The light analysis needs to be done only when it is NOT NIGHT
        curr_hour = int(self.current_time.split(':')[0])

        light_lst = []
        for meas in self.devices_meas[str(device_id)]["Light Intensity"]:
            # The light measurements which are the ones less old than half an hour
            # ALWAYS
            if (self.current_timestamp - meas['t']) < 1800:
                light_lst.append(meas['v'])
        
        light_avg = sum(light_lst)/len(light_lst)

        # Moonlight reaches values of 0.1... 
        # --> this should be enough to detect day vs. night
        if light_avg > 2 and curr_hour > 5 and curr_hour < 23:
            # Validation of the results
            rain = pred_weather.values
            if not rain:
                # look at light: if low then cloudy, else
                if light_avg > LIGHT_SUNNY:
                    return 0, 'day'
                else:
                    return -1, 'day'
            else:
                return rain, 'day'
        else:
            return pred_weather.values, 'night'

    def estFutureWeather(self, device_id=None, time_range=24*3600, test_el=None, model=None, model_path="models/rain_tomorrow.sav"):
        """
        Perform estimation of precipitations for the next day, given the values gathered in the
        last 'time_range' (default 24 hours) and today's precipitations.
        ---
        Input parameters:
        - device_id (int): id of the device whose measurements have to be used
        - time_range (int, default 24*3600): maximum age of the considered data - in s
        - test_el (pd.Series, default None): optional input data alreafy evaluated.
        - model (sklearn model, fitted, default None): optional model to be used,
        must be already trained
        - model_path (default models/weather_today.sav): path specifying the model 
        (.sav file that can be opened with pickle)
        """
        # To get the future weather (done typically once a day at 10 pm), the 
        # model needs to know whether it rained today. Therefore, before the 
        # actual prediction is done, it is necessary to evaluate the presence 
        # of rain in the past 24 hours

        self.updateTime()

        if device_id is None:
            if len(self.devices_meas) > 0:
                # Find 'first' device for which ALL the measurements lists are not empty
                # This prevents to choose devices which may have disconnected
                i = 0
                ok = False
                while i < len(self.devices_meas) and not ok:
                    k = list(self.devices_meas.keys())[i]
                    i += 1
                    ok = True
                    for m in self.devices_meas[k].keys():
                        if self.devices_meas[k][m] == []:
                            ok = False
                
                if i <= len(self.devices_meas):
                    device_id = k            
                else:
                    print("Unable to get measurements - no complete set!")
            else:
                print("No available measurements to be used!")
                return None, ''
        
        assert (device_id is not None), "Invalid device_id"
        
        if test_el is None:
            try:
                test_el = self.evalMeasPrediction(time_range, device_id)
            except:
                print("Unable to get measurements!")
                return None, ''

        assert (not test_el.isnull().values.any()), "NaN detected"

        if model is None:
            # Extract model:
            with open(model_path, 'rb') as f:
                load_model = pickle.load(f)
        else:
            load_model = model
        
        pred_today_rain = self.estCurrWeather(device_id, time_range, test_el)[0]
        
        assert (pred_today_rain is not None),  "pred_today_rain"

        # Make output either 1 (rain) or 0 (no rain)
        if pred_today_rain != 1:
            pred_today_rain = 0

        new_test = test_el.copy()
        new_test["FENOMENI"] = pred_today_rain

        pred_tomorrow_rain = futureRain_2(new_test, load_model)

        return pred_tomorrow_rain.values

#

class WeatherStationWS():
    """
    Web service for the weather station.
    """
    exposed = True

    def __init__(self, conf_file="weather_station_conf.json", out_conf="weather_station_conf_updated.json", own_ID=False):
        """
        Initialization procedure:
        - Import conf file
        - Create service catalog address and save in one variable the data to be uploaded 
        on the services catalog (weather station info)
        - Extract the locations (paths) of the prediction models used in the algorithms (weather evaluation and forecasting)
        - If manually assigned, set ID (else None)
        - Attempt registration at services catalog (uploading self information)
        - Get broker
        - Initialize and launch MQTT client
        - Instantiate weather station and initialize empty devices list catalog
        """

        self._conf_path = conf_file
        try:
            with open(conf_file) as f:
                self._conf = json.load(f)
        except:
            with open("weather/" + conf_file) as f:
                self._conf = json.load(f)

        self._serv_cat_addr = "http://" + self._conf["services_catalog"]["ip"] + ":" + str(self._conf["services_catalog"]["port"])    # Address of services catalog
        self.whoami = self._conf["weather_station"]         # Own information - to be sent to the services catalog
        
        for ed in self.whoami["endpoints_details"]:
            if ed["endpoint"] == "REST":
                self.ip = ed["address"].split(':')[1].split('//')[1]
                self.port = int(ed["address"].split(':')[-1])
        
        # Prediction model binary file paths
        self.pred_model_today = self._conf["models_path"]["today"]
        self.pred_model_tomorrow = self._conf["models_path"]["tomorrow"]

        if own_ID:
            self.id = self.whoami["id"]
        else:
            # If the ID was not manually assigned (in the conf), the initial value is set to None
            self.id = None

        # HTTP conf
        self._http_conf = {
                '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True
            }
        }

        # Connect to the services catalog
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
        # List of topics to subscribe to as the weather
        self.topics_list = []

        # Connect to the broker
        self.mqtt_cli.start()

        self.weather_station = WeatherStation()
        
        self._dev_cat_info = {}
        # The devices list consists of a dict with a list (actual list of devices 
        # as stored in the devices catalog) and the last update field
        # NOTE: last_update is an Unix timestamp
        self._devices = {
            "list": [],
            "last_update": 0
        }

    ################################################################
    # REST methods
    
    def GET(self, *uri, **params):
        # Can get: curr_weather, tomorrow_rain
        if len(uri) > 0:
            if str(uri[0]) == "curr_weather":
                # Retrieve the current weather (from values of last hour)
                self.weather_station.cleanupMeas()
                if len(params) > 0 and str(params.keys(0)) == "id":
                    curr_weather, val = self.weather_station.estCurrWeather(int(params["id"]), model_path=self.pred_model_today)
                else:
                    curr_weather, val = self.weather_station.estCurrWeather(model_path=self.pred_model_today)

                if curr_weather == 1:
                    return "rain"
                elif curr_weather == 0 and val == 'day':
                    return "sun"
                elif curr_weather == 0 and val == 'night':
                    return "clear"      # No rain at night
                elif curr_weather == -1:
                    return "clouds"
                
            elif str(uri[0]) == "will_it_rain":
                # Anticipate tomorrow's weather given the last 24 hours
                self.weather_station.cleanupMeas()
                if len(params) > 0 and str(params.keys(0)) == "id":
                    next_rain = self.weather_station.estFutureWeather(int(params["id"]), model_path=self.pred_model_tomorrow)
                else:
                    ### HERE
                    next_rain = self.weather_station.estFutureWeather(model_path=self.pred_model_tomorrow)
                
                assert (next_rain is not None), f"Value: {next_rain}"

                if next_rain == 1:
                    return "yes"
                elif next_rain == 0:
                    return "no"
        else:
            return "Available uri:\n/curr_weather\n/tomorrow_rain"

    ################################################################

    def notify(self, topic, payload):
        """
        Callback for MyMQTT - at message reception
        ---
        As the message is received, it is passed to the method 
        self.weather_station.addMeasurement alongside with the device ID.
        
        The device ID is inferred from the topic, as it is 
        designed to follow a standard syntax.
        """
        print(f"Received message in {topic}")
        
        id = int(topic.split('/')[1])
        
        if self.weather_station.addMeasurement(json.loads(payload), dev_id=id) == 0:
            print(f"Unable to add measurement!\n{payload}")
        
        # Also perform cleanup of the records
        self.weather_station.cleanupMeas()

    ################################################################

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
        tries = 0
        while not self._registered_at_catalog and tries < max_tries:
            # Probably will need to assign id here ...


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
                tries += 1
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
        while self._dev_cat_info == {} and tries < max_tries:
            addr = self._serv_cat_addr + "/device_catalog"
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

        The max age is 'timeout' (default 240s - 4 min).
        """
        if self._dev_cat_info != {}:
            curr_time = time.time()
            if (curr_time - self._dev_cat_info["last_update"]) > timeout:
                self._dev_cat_info = {}

    def getListOfDevices(self, max_tries=25, info_timeout=120):
        """
        Get the list of connected devices from the device catalog.
        
        Need to check carefully the response code! (The devices list may be empty)
        ---
        Return values:
        - 1: success
        - 0: Unable to get list of devices
        - -1: Unable to get device catalog info
        """
        
        # CHeck device cat info exists:
        if self._dev_cat_info == {}:
            if self.getDevCatInfo() == 0:
                print("Unable to get device catalog info")
                return -1
        
        # The retrieval is done only if the current info is more then 'info_timeout' seconds old
        # Need to call this method periodically (main loop)     
    
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
        """
        Reset the information about the devices - reset devices list
        ---
        Input parameter:
        - info_timeout: maximum age of information in seconds
        """
        if (time.time() - self._devices["last_update"]) > info_timeout:
            self._devices = {
                "list": [],
                "last_update": 0
            }
            return 1
        return 0

    def subscribeToTopics(self, info_timeout=120):
        """
        Need to read list of devices (from getListOfDevices) and for each sensor get the topics.
        - Check for each topic not to be among the topics we are already subbed to
        - Check for topic compatibility with needed measurements
        - Subscribe to the topic if both checks are passed
        - Add the topic to the list of ones to which we are subscribed

        To be ran periodically
        ---
        The returned value is the number of new topics to which the program subscribed
        """
        # First, check the devices list is empty or outdated
        if self._devices["list"] == [] or (time.time() - self._devices["last_update"]) > info_timeout:
            # Attempt to retrieve info
            self.getListOfDevices()

        if self._devices["list"] != []:
            # Iterate over the list of sensors and get topics
            # Before subbing, check the topic is not already in the list of topics
            # self.topics_list and only sub if the last element in the topic 
            # is an element of self.weather_station.relevant_meas_short

            # Reach the topics list
            n_sub = 0
            for dev in self._devices["list"]:
                for sens in dev["resources"]["sensors"]:
                    if "MQTT" in sens["available_services"]:
                        for det in sens["services_details"]:
                            if det["service_type"] == "MQTT":
                                for top in det["topic"]:
                                    if top.split('/')[-1] in self.weather_station.relevant_meas_short and top not in self.topics_list:
                                        # Sub to the topic
                                        self.mqtt_cli.mySubscribe(top)
                                        # Add topic to the list
                                        self.topics_list.append(top)
                                        n_sub += 1
            
            return n_sub

    def postToMongoDB(self, max_tries=2):
        # Get mongoDB info from serv cat
        mdb_info = {}
        tries = 0
        addr = self._serv_cat_addr + '/service?name=mongoDB'
        while mdb_info == {} and tries < max_tries:
            tries += 1
            
            try:
                r = requests.get(addr)
                mdb_info = r.json()
                if r.ok:
                    print("MongoDB info retrieved")
                else:
                    print("Unable to get mongoDB info")
                    time.sleep(3)
            except:
                print("Unable to reach services catalog to get MongoDB info!")
                time.sleep(3)
        
        if mdb_info == {}:
            print("Could not get MongoDB info")
            return 0
        
        # We need to post the data for the whole day:

        # Check there are available devices:
        if len(self._devices["list"]) > 0:
            # Data series
            my_id = self._devices["list"][0]["id"]
            dataSeries = self.weather_station.evalMeasPrediction(time_range=24*3600, dev_id=my_id)
            today_wttr, ddd = self.weather_station.estCurrWeather(device_id=my_id, time_range=24*3600, )

            tbs = {}
            for k in COLS_FUTURE:
                if k != "FENOMENI":
                    tbs[k] = dataSeries[k]
                else:
                    if today_wttr == 1:
                        tbs[k] = 1
                    else:
                        tbs[k] = 0
            
            # Having filled the dict, we can send it to MongoDB
            addr_mdb = mdb_info["endpoints_details"][0]["address"]
            
            tries = 0
            while tries < max_tries:
                tries += 1
                try:
                    r_up = requests.post(addr_mdb, json.dumps(tbs))
                    if r_up.ok:
                        print("Posted!")
                        return 1
                    else:
                        print("Unsuccessful POST")
                except:
                    print("Unable to reach MongoDB adaptor")

        else:
            print("No devices to get the measurements from!")
            return 0

    def launch(self):
        """
        Launch the web service.
        """
        cherrypy.tree.mount(self, '/', self._http_conf)
        cherrypy.config.update({'server.socket_host': self.ip})
        cherrypy.config.update({'server.socket_port': self.port})
        cherrypy.engine.start()
      
    def mainLoop(self, hour_update):
        # This method performs:
            # Serv. cat. update
            # Dev. list retrieval
            # Topic subscription
            # Update of the weather to MongoDB every 24 hours (at 11 pm)
        
        already_sent_flg = False

        timeout = time.time() + 10

        datetime_now = datetime.fromtimestamp(time.time())
        datetime_tonight = datetime(datetime_now.year, datetime_now.month, datetime_now.day, 20, 00)
        
        print(datetime_now)
        print(datetime_tonight)

        timeout = datetime_tonight.timestamp()

        while True:
            time.sleep(5)

            # Send data to mongoDB now
            curr_hour = int(datetime.now().strftime("%H"))
            if curr_hour >= hour_update or curr_hour < ((hour_update+1)%24) and not already_sent_flg:
                # Will be activated the first iteration after 23:00
                
                already_sent_flg = True
            elif curr_hour <= hour_update and curr_hour > ((hour_update+1)%24) and already_sent_flg:
                # Reset the flag to 
                already_sent_flg = False

            self.updateServiceCatalog()
            self.getDevCatInfo()
            self.getListOfDevices()
            self.subscribeToTopics()
            
            if time.time() > timeout:
                print(datetime.fromtimestamp(time.time()))
                self.postToMongoDB()

                # datetime_tonight = datetime_tonight.timedelta(days=1)
                datetime_tonight += timedelta(minutes=4)
                timeout = datetime_tonight.timestamp()
            
            # These 2 will work iff the weather station is not able 
            # to update the info for some time
            self.cleanupDevCatInfo()
            self.clearDevicesList()

#       
#
#

if __name__ == "__main__":
    my_weather_station = WeatherStationWS(own_ID=True)
    my_weather_station.launch()

    try:
        my_weather_station.mainLoop(hour_update=23)
    except KeyboardInterrupt:
        cherrypy.engine.stop()
        traceback.print_exc()
        sys.exit(1)
