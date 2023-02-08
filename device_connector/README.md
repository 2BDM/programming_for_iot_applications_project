# Device Connector

This folder contains the main program, which runs the device connector for the raspberry pi.

## Working principle

The device connector consists in a program which on one side interfaces with the sensors and actuators to either publish MQTT messages or react to them, on the other must interface with the registry system (service and device catalog) to always keep the information updated.

### Device agents

Device agents are implemented as pieces of software (classes) which are instantiated at initialization only if the device uses these objects.
This mechanism is designed to guarantee interoperability between the different possible sensors that can be used.
At initialization of the device connector, the program will iterate over the list of sensors and initialize the correct device agent, which will be appended to the `self.dev_agents` list. To map the name of the sensor to the positional index within the list, the dict `self.dev_agent_ind` is used (given the *sensor name*, it returns the correct device agent).

### Device agents API

Each device agent (class) must have a `measure()` method, which returns all measurements (or lists of measured values) in SenML format:

    {"n": "Measured quantity", "u": "Unit of meas", "t": timestamp , "v": measured_value}

### Last measurements

The list `self.last_meas` contains the last measurements for each measured quantity. It is created by reading the available quantities to be measured inside the lists `measure_type` found in the device information.

`self.last_meas` is actually a list of lists, each of which contains all (last) measurements available from each sensor. The positional indexing reflects that of `self.dev_agents_sens`, meaning the correct measurements can be accessed by making use of `self.device_agent_ind_sens`.

### MQTT topics - sensors

All sensor measurements are published via MQTT on the broker.
The `publishLastMeas()` method performs the publication, acting as follows:

- Iterate through sensor list in the device information dict (`self.whoami`)
- Retrieve the last measurements for each sensor (using the name-index mapping as explained in 'Last measurements')
- Get list of topics assoc. with the sensor
- For each entry in the selected last-measured list, find the associated topic, knowing the last element in the topic url is the name of the measurement (associated with key `"n"` in the SenML-compliant measure info), **all lowercase and with spaces replaced by underscores**.
- Publish the SenML message containing the measure in the topic
