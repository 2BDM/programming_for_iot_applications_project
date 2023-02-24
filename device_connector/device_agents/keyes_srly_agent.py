import time
import warnings
import json
import sys

# Allow operation even if not on pi
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    on_pi = True
except:
    on_pi = False


def act_open(pin):
    """ Open the relay switch """
    GPIO.output(pin, GPIO.LOW)

def act_close(pin):
    """ Close the relay switch """
    GPIO.output(pin, GPIO.HIGH)


class KeyesSRLYAgent():

    def __init__(self, conf=None, off_state="open"):
        """
        This class is used to control the KeyesSRLY actuator module.
        It is possible to give commands to turn on or off.
        ---------------------------------------------------------------
        Parameters:
        - conf: configuration file (json)/dict. It must contain the 
        key 'dt', corresponding to the number of the pin to which the
        actuator is connected
        - off_state: can be "open" or "closed". Depending on this, 
        either state is associated with the state 'off'.
        ---------------------------------------------------------------
        """

        if conf is None and on_pi:
            raise ValueError("The Keyes SRLY agent was not provided a conf file!")
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

        # Select correct pin, from conf
        if on_pi:
            self._pin = int(self.config["dt"])
            GPIO.setup(self._pin, GPIO.OUT)
        else:
            self._pin = None

        # Via the parameter 'off_state', one can set the off position of the 
        # (device connected to the) relay

        # The actuator is ALWAYS INITIALIZED AS OFF
        self.off_state = off_state
        if off_state == "open":
            if on_pi:
                act_open(self._pin)
            self.state = 'off'
            self._act_state = 'open'
        elif off_state == "closed":
            if on_pi:
                act_close(self._pin)
            self.state = 'off'
            self._act_state = 'closed'
        else:
            raise ValueError("Invalid off_state selected! Possible values: 'open', 'closed'")
        

    def isOn(self):
        if self.state == 'on':
            return True
        
        return False
    
    def start(self):
        """
        This method switches the actuator to the 'on' state
        
        Returned values:
        - 1: turned on correctly
        - 0: already on
        """
        if on_pi:
            if self.off_state == 'open':
                act_close(self._pin)
            elif self.off_state == 'closed':
                act_open(self._pin)
    
        if self.state == 'off':
            self.state = 'on'
            return 1
        else:
            return 0
        
    def stop(self):
        """
        This method switches the actuator to the 'off' state
        
        Returned values:
        - 1: turned off correctly
        - 0: already off
        """
        if on_pi:
            if self.off_state == 'open':
                act_open(self._pin)
            elif self.off_state == 'closed':
                act_close(self._pin)
    
        if self.state == 'on':
            self.state = 'off'
            return 1
        else:
            return 0
        
    def stop_operation(self):
        """
        This method stops the activity of the actuator

        WARNING: this method stops all GPIO activity on the Raspberry!
        """
        if on_pi:
            GPIO.cleanup()
        return


if __name__ == "__main__":
    sample_conf = {
        "name": "Keyes_SRLY",
        "id": 1,
        "dt": 21
    }

    my_act = KeyesSRLYAgent(conf=sample_conf)

    my_act.start()
    time.sleep(2)
    my_act.stop()
    time.sleep(2)
    my_act.start()
    time.sleep(2)
    my_act.stop()

    my_act.stop_operation()