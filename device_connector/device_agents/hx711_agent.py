import json
import time
import random
import warnings
import sys

# The program will try to infer whether it is running on the RPi
try:
    from hx711 import HX711
    on_pi = True
except:
    on_pi = False

"""
This device agent is used to communicate with the BMP180 sensor
which is used to obtain measurements about the atmophteric 
pressure, temperature (and altitude).
"""

class HX711Agent():
    def __init__(self, conf=None):
        """
        The class HX711Agent is used as the device agent for the HX711 - an ADC 
        used to read load cells values.
        The required parameter at initialization is 'conf', being either the conf
        file path (json) or the dictionary itself.
        """
        
        ## NOTE: the configuration is not necessary since the sensor uses the I2C bus
        # but still it's something nice to have
        if conf is None:
            warnings.warn("Missing conf for HX711!")
            self.config = None
        elif isinstance(conf, str):
            try:
                with open(conf) as fp:
                    self.config = json.load(fp)
                    print("Conf file opened!")
            except OSError:
                print(f"Unable to open conf file {conf}")
                sys.exit()
        elif isinstance(conf, dict):
            self.config = conf


        if self.config is not None:
            self._name = self.config["name"]
            self._dt_pin = int(self.config["dt"])
            self._sck_pin = int(self.config["sck"])
        else:
            # Default i2c bus pins for RPi3
            self._dt_pin = 3
            self._sck_pin = 5
        
        # If the library was found, then we can access the 
        # sensor to perform measurements
        if on_pi:
            self._sensor = HX711(
                            dout_pin=self._dt_pin,
                            pd_sck_pin=self._sck_pin,
                            channel='A',
                            gain=64
                        )
            self._sensor.reset()
        else:
            self._sensor = None

        self.wt_template = {
            "n": "Tank Weight",
            "u": "g",
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
        meas_wt = None

        # Set a max. n. of tries to try to avoid invalid values
        max_tries = 25
        tries = 0
        while tries < max_tries and meas_wt is None:
            tries += 1

            # If the library was available, then the program can 
            # perform the measurements
            if on_pi:
                meas_wt = self._sensor.get_raw_data(num_measures=5)
            else:
                meas_wt = round(random.uniform(0, 100), 2)

        msg_wt = self.wt_template.copy()
        msg_wt["t"] = time.time()
        msg_wt["v"] = meas_wt

        out = [msg_wt]

        return out


### Program demo - can be used for testing
if __name__ == "__main__":
    sample_conf = {
        "name": "HX711",
        "dt": 3,
        "sck": 5
    }
    
    agent = HX711Agent(sample_conf)

    if agent._sensor is None:
        print("Library not detected!")
    else:
        print("Current measurements: ")
        for meas in agent.measure():
            print(f"{meas}")
