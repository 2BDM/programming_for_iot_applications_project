# Device Connector

This folder contains the main program, which runs the device connector for the raspberry pi.

## Working principle

The device connector consists in a program which on one side interfaces with the sensors and actuators to either publish MQTT messages or react to them, on the other must interface with the registry system (service and device catalog) to always keep the information updated.

### Device agents

Device agents are implemented as pieces of software (classes) which are instantiated at initialization only if the device uses these objects.
This mechanism is designed to guarantee interoperability between the different possible sensors that can be used.
At initialization of the device connector, the program will iterate over the list of sensors and initialize the correct device agent, which will be appended to the `self.dev_agents` list. To map the name of the sensor to the positional index within the list, the dict `self.dev_agent_ind` is used (given the *sensor name*, it returns the correct device agent).

### Last measurements

The list `self.last_meas` contains the last measurements for each measured quantity. It is created by reading the available quantities to be measured inside the lists `measure_type` found in the device information.
