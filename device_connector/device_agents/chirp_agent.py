import json
import time
import random
import warnings
import sys

# The program will try to infer whether it is running on the RPi
# try:
#     import ???
#     on_pi = True
# except:
on_pi = False

########## --> Currently no sensor is available

"""
This device agent is used to communicate with the 'chirp' sensor
which is used to obtain measurements about the soil moisture.
"""

class ChirpAgent():
    def __init__(self, conf=None):
        """
        The class ChirpAgent is used as the device agent for the chirp sensor.
        The required parameter at initialization is 'conf', being either the conf
        file path (json) or the dictionary itself.
        """
        
        ## NOTE: the configuration is not necessary since the sensor uses the I2C bus
        # but still it's something nice to have
        if conf is None:
            warnings.warn("Missing conf for Chirp!")
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

        # If the library was found, then we can access the 
        # sensor to perform measurements
        # if on_pi:
        #     self._sensor = BMP085.BMP085()
        # else:
        self._sensor = None
        
        if self.config is not None:
            self._name = self.config["name"]
            self._pin = int(self.config["dt"])

        self.sm_template = {
            "n": "Soil moisture",
            "u": "%",
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
        meas_sm = None

        # Set a max. n. of tries to try to avoid invalid values
        max_tries = 25
        tries = 0
        while tries < max_tries and meas_sm is None:
            tries += 1

            # If the library was available, then the program can 
            # perform the measurements
            if on_pi:
                pass
            else:
                meas_sm = round(random.uniform(1, 99), 2)

        msg_sm = self.sm_template.copy()
        msg_sm["t"] = time.time()
        msg_sm["v"] = meas_sm

        out = [msg_sm]

        return out


### Program demo - can be used for testing
if __name__ == "__main__":
    sample_conf = {
        "name": "chirp",
        "dt": 3,
        "sck": 5
    }
    
    agent = ChirpAgent(sample_conf)

    if agent._sensor is None:
        print("Library not detected!")
    else:
        print("Current measurements: ")
        for meas in agent.measure():
            print(f"{meas}")
