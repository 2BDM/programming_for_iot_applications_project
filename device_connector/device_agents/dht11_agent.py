<<<<<<< HEAD
import random as rnd

class DHT11Agent:
    def __init__(self):
        self.type = "DHT11"
        self.dict_temp_hum = {"humidity":0,"temperature":0}
        
    def take_measure(self):
        self.updateTemp()
        self.updateHum()
        return self.dict_temp_hum
    
    def updateTemp(self):
        self.dict_temp_hum["temperature"]=rnd.randint(18,25)
        
    
    def updateHum(self):
        self.dict_temp_hum["humidity"]=rnd.randint(50,80)    
=======
import json
import time
import random
import sys
import Adafruit_DHT

# NOTE: this program can only run on the raspberry pi!

class DHT11Agent:
    """
    Class for DHT11 sensor, which measures temperature and humidity
    """
    def __init__(self, conf):
        """
        - conf: path of the configuration file 
          OR configuration dict
        """
        #
        if isinstance(conf, str):
            try:
                with open(conf) as fp:
                    self.config = json.load(fp)
                    print("Conf file opened!")
            except OSError:
                print(f"Unable to open conf file {conf}")
                sys.exit()
        elif isinstance(conf, dict):
            self.config = conf

        self._name = self.config["name"]
        self._sensor = Adafruit_DHT.DHT11
        self._pin = int(self.config["dt"])

        # Temperature measurement: degrees Celsius
        self.temp_template = {
            "n": "Temperature",
            "u": "Cel",
            "t": 0,
            "v": 0
        }

        # Humidity measure: relative humidity - expressed in percentage
        self.hum_template = {
            "n": "Humidity",
            "u": "%",
            "t": 0,
            "v": 0
        }

    
    def measure(self):
        meas_t = None
        meas_h = None

        # Set a max. n. of tries to try to avoid invalid values
        max_tries = 25
        tries = 0
        while tries < max_tries and (meas_t is None or meas_h is None):
            tries += 0
            meas_h, meas_t = Adafruit_DHT.read_retry(self._sensor, self._pin)

        msg_t = self.temp_template.copy()
        msg_t["t"] = time.time()
        msg_t["v"] = meas_t

        msg_h = self.hum_template.copy()
        msg_h["t"] = time.time()
        msg_h["v"] = meas_h

        out = []

        if meas_t is not None:
            out.append(msg_t)
        
        if meas_h is not None:
            out.append(msg_h)

        return out
        
        
>>>>>>> 838665f44b1fa9770c5bda4940a2b70dd244120d
