import json
import time
import random
import sys

# The program will try to infer whether it is running on the RPi
try:
    import Adafruit_BMP
    on_pi = True
except:
    on_pi = False

"""
This device agent is used to communicate with the BMP180 sensor
which is used to obtain measurements about the atmophteric 
pressure, temperature (and altitude).
"""

class BMP180_agent():
    def __init__(self, conf):
        """
        The class BMP180_agent is used as the device agent for the BMP180 sensor.
        The required parameter at initialization is 'conf', being either the conf
        file path (json) or the dictionary itself.
        """
        
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
            self._sensor = Adafruit_BMP.BMP085.BMP085()
        else:
            self._sensor = None
        
        self._name = self.config["name"]
        self._pin = int(self.config["dt"])

        self.temp_template = {
            "n": "Temperature",
            "u": "Cel",
            "t": 0,
            "v": 0
        }

        self.press_template = {
            "n": "Pressure",
            "u": "Pa",
            "t": 0,
            "v": 0
        }


    def measure(self):
        """
        This method is used to perform all the possible measurements
        which can be done by the sensor and output them following 
        the SenML format.
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
                meas_t = self._sensor.read_temperature()
                meas_p = self._sensor.read_pressure()
            else:
                meas_t = round(random.uniform(18, 30), 2)
                meas_p = round(random.uniform(99000, 110000), 2)

        msg_t = self.temp_template.copy()
        msg_t["t"] = time.time()
        msg_t["v"] = meas_t

        msg_h = self.press_template.copy()
        msg_h["t"] = time.time()
        msg_h["v"] = meas_p

        out = []

        return out


if __name__ == "__main__":
    pass
