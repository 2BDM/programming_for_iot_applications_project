import cherrypy
import json
import time
from datetime import datetime
import sys
from sub.MyMQTT import MyMQTT
import requests
import warnings

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

        # TODO: decide and initialize the data structure to store past measurements into
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

    def evalMeasPrediction(self, ):
        """
        Used to evaluate the measurements for the prediction strategy.
        It also adds the season using the current date.

        Measurements for weather:
        - Average temp (cel)
        - Min temp (cel)
        - Max temp (cel)
        - Humidity (%)
        - Pressure (mb relative to sea level) --> Use convertion method
        """
        self.updateTime()

        pass



class WeatherStationWS():

    def __init__(self, conf_file="weather_station_conf.json", out_conf="weather_station_conf_updated.json", own_ID=False):
        """
        
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
        
        self._mqtt_client = None

    
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
