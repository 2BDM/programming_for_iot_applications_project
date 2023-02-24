import json
import time
import random
import warnings
import sys

# Allow the program to behave as a number generator if 
# the library is not found
try:
    import adafruit_bh1750
    import board
    on_pi = True
except:
    on_pi = False

class BH1750Agent:
    """
    Class for BH1750(FVI) sensor, which measures light intensity
    """
    def __init__(self, conf=None):
        """
        - conf: path of the configuration file 
          OR configuration dict
        """
        #
        if conf is None:
            warnings.warn("Missing conf for BH1750!")
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

        if on_pi:
            self._i2c = board.I2C()
            self._sensor = adafruit_bh1750.BH1750(self._i2c)
        else:
            self._sensor = None
        
        if self.config is not None:
            self._name = self.config["name"]
            self._pin = int(self.config["dt"])

        # Light intensity measurement: Lux
        self.light_template = {
            "n": "Light Instensity",
            "u": "Lux",
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
        
        meas_li = None

        # Set a max. n. of tries to try to avoid invalid values
        max_tries = 25
        tries = 0
        while tries < max_tries and (meas_li is None):
            tries += 1
            
            if on_pi:
                meas_li = self._sensor.lux
            else:
                meas_li = round(random.uniform(0.5, 10000), 2)

        msg_li = self.light_template.copy()
        msg_li["t"] = time.time()
        msg_li["v"] = meas_li

        out = []

        return out
    

### Program demo - can be used for testing
if __name__ == "__main__":
    sample_conf = {
        "name": "BH1750",
        "dt": 3,
        "sck": 5
    }
    
    agent = BH1750Agent(sample_conf)

    if agent._sensor is None:
        print("Library not detected!")
    else:
        print("Current measurements: ")
        for meas in agent.measure():
            print(f"{meas}")
