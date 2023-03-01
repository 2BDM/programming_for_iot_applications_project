import cherrypy
import json
import time
import pandas as pd
from datetime import datetime
import sys
from sub.MyMQTT import MyMQTT
import requests
import warnings
import pickle

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
        self.meas_timeout = 24*60*60        # Timeout for forgetting the measurements, in seconds
        self.execution_time = "22:00"
        self.current_datetime = datetime.now()                          # !!! datetime object
        self.current_timestamp = time.mktime(self.current_datetime.timetuple())
        self.current_time = self.current_datetime.strftime("%H:%M")     # String
        self.current_date = self.current_datetime.strftime("%Y-%m-%d")  # String (compliant with timestamps)
        self.current_season = MONTH2SEASON[str(datetime2monthNumber(self.current_date))]    # String


        # Relevant measurements: the ones for which measurements are needed
        self.relevant_meas_short = [
            "temperature",
            "humidity",
            "air_pressure",
            "light_intensity"
        ]

        self.relevant_meas = {
            "Temperature",
            "Humidity",
            "Air Pressure",
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
        self.current_season = MONTH2SEASON[str(datetime2monthNumber(self.current_date))]


    def addMeasurement(self, newSenML, dev_id=None):
        """
        Add a new measurement in the local list of measurements.

        newSenML is the senML-compliant message directly obtained via MQTT 
        (payload) - the device ID must be specified by the user (look at the topic of the rx message)

        If not specified, the device ID is inferred from the base name in the senML message

        If the insertion is successful, the return value is 1, else it is 0
        (meaning the attempt generated a python error)
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

        try:
            meas_type = newSenML['e']['n']
            
            meas = {            # To be appended in dict
                'v': newSenML['e']['v'],
                'u': newSenML['e']['u'],
                't': newSenML['e']['t']
            }

            # Insert meas:
            self.devices_meas[id][meas_type].append(meas)

            return 1
        except:
            # Hopefully never...
            return 0


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
            for n in id.keys():
                # Iterate over the list
                stop = False
                i = 0
                while i < len(id[n]) and stop == False:
                    ## TODO: test this - pointers should do the job
                    
                    # NOTE: the index is actually always 0, since we remove from the 1st element
                    # It is needed in the case the list is completely emptied
                    if (ts - id[n][i]['t']) > to:
                        # Old --> remove it
                        id[n].pop(i)
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
        p_mean = sum(taken_cat["Air Pressure"])/len(taken_cat["Air Pressure"])

        # Season:
        seas = MONTH2SEASON[str(datetime2monthNumber(self.current_datetime))]
        seas_id = SEASON2ID[seas]

        out = pd.Series([t_mean, t_min, t_max, h_mean, p_mean, seas_id], index=COLS_CURRENT)
        
        return out


    def estCurrWeather(self, device_id, time_range=7400, test_el=None, model=None, model_path="models/weather_today.sav"):
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
        """
        # The sklearn model is used to estimate the presence of rain. This 
        # estimate is then compared with the measurements about the light 
        # intensity of today, hence it is also possible to estimate the 
        # weather as simply 'cloudy'
        # Alternatives: sunny, cloudy, rainy

        self.updateTime()

        if test_el is None:
            # If here, the device ID MUST BE PRESENT
            test_el = self.evalMeasPrediction(time_range, device_id)

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
        for meas in self.devices_meas[device_id]["Light Intensity"]:
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


    def estFutureWeather(self, device_id, time_range=24*3600, test_el=None, model=None, model_path="models/weather_today.sav"):
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

        if test_el is None:
            test_el = self.evalMeasPrediction(time_range, device_id)

        if model is None:
            # Extract model:
            with open(model_path, 'rb') as f:
                load_model = pickle.load(f)
        else:
            load_model = model
        
        pred_today_rain = self.estCurrWeather(device_id, time_range, test_el)[0]

        new_test = test_el.copy()
        new_test["FENOMENI"] = pred_today_rain

        pred_tomorrow_rain = futureRain_2(new_test, load_model)

        return pred_tomorrow_rain.values



class WeatherStationWS():

    def __init__(self, conf_file="weather_station_conf.json", out_conf="weather_station_conf_updated.json", own_ID=False):
        """
        Web service for the weather station.

        """

        self._conf_path = conf_file
        try:
            with open(conf_file) as f:
                self._conf = json.load(f)
        except:
            with open("weather/" + conf_file) as f:
                self._conf = json.load(f)

        self._serv_cat_addr = "http://" + self._conf["services_catalog"]["ip"] + ":" + self._conf["services_catalog"]["port"]    # Address of services catalog
        self.whoami = self._conf["weather_station"]         # Own information - to be sent to the services catalog
        
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

        # TODO: Connect to the services catalog
        
        self._mqtt_client = None

        self._weather_station = WeatherStation()

    
    def notify(self):
        """
        Callback for MyMQTT - at message reception
        ---
        What to do: 
        - Extract measurement
        - Store it in current device information
        """
        pass

    def registerAtServCat(self):
        pass

    def getDevCatInfo(self):
        pass

    def getListOfDevices(self):
        """
        Need to check carefully the response code! (The devices list may be empty)
        """
        pass

    def subscribeToTopics(self):
        """
        Need to read list of devices (from getListOfDevices) and for each sensor get the topics.
        - Check for each topic not to be among the topics we are already subbed to
        - Check for topic compatibility with needed measurements
        - Subscribe to the topic if both checks are passed
        - Add the topic to the list of ones to which we are subscribed

        To be ran periodically
        """
        pass
        


        



if __name__ == "__main__":
    pass
