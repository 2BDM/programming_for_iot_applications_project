import json
import time
import random
import sys

# Allow the program to behave as a number generator if 
# the library is not found
try:
    import Adafruit_DHT
    on_pi = True
except:
    on_pi = False

class DHT11Agent:
    """
    Class for DHT11 sensor, which measures temperature and humidity
    """
    def __init__(self, conf=None):
        """
        - conf: path of the configuration file 
          OR configuration dict
        """
        # Check conf - in this case it is required, since the sensor does not
        # run on the i2c bus
        if conf is None:
            raise ValueError("Missing DHT11 configuration!")

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

        if on_pi:
            self._sensor = Adafruit_DHT.DHT11
        else:
            self._sensor = None
        
        self._name = self.config["name"]
        self._pin = int(self.config["out"])

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
        """
        The measurements are returned in SenML format.
        -------------------------------------------------------------
        If the measure is not obtained, the measurement is None.
        This means that the program calling the agent needs to handle
        missing values.
        """
        
        meas_t = None
        meas_h = None

        # Set a max. n. of tries to try to avoid invalid values
        max_tries = 25
        tries = 0
        while tries < max_tries and (meas_t is None or meas_h is None):
            tries += 1
            
            if on_pi:
                meas_h, meas_t = Adafruit_DHT.read_retry(self._sensor, self._pin)
            else:
                meas_h = round(random.uniform(20, 60), 2)
                meas_t = round(random.uniform(18, 35), 2)

        msg_t = self.temp_template.copy()
        msg_t["t"] = time.time()
        msg_t["v"] = meas_t

        msg_h = self.hum_template.copy()
        msg_h["t"] = time.time()
        msg_h["v"] = meas_h

        out = []

        return out
    

### Program demo - can be used for testing
if __name__ == "__main__":
    sample_conf = {
        "name": "DHT11",
        "dt": 7
    }
    
    agent = DHT11Agent(sample_conf)

    if agent._sensor is None:
        print("Library not detected!")
    else:
        print("Current measurements: ")
        for meas in agent.measure():
            print(f"{meas}")
