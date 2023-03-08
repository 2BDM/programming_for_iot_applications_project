# Device Connector

This folder contains the main program, which runs the device connector for the raspberry pi.

## Working principle

The device connector consists in a program which on one side interfaces with the sensors and actuators to either publish MQTT messages or react to them, on the other must interface with the registry system (service and device catalog) to always keep the information updated.
The device connector also acts as HTTP server, by advertising the GET method, through which it is possible to retrieve the last valid measurements for any quantity and sensor.

The device connector ID is not user-defined (despite the 'id' field being present in the initial device info). The first time, before registering to the device catalog, the connector will request a new (available) ID and use that one.

---

## Launching the container

**Important notice**: the device connector requires the use of device agents, which are software components used to communicate with the different sensors. In order to allow for different sensors to be used, the file 'requirements.txt' does not include all the needed packages. In any case, the provided device agents have been built in such a way that they will detect missing packages (i.e., missing sensors) and in this case their `measure` method will simply return random numbers as measurements.
The user also needs to correctly specify the ID of his own device.

In order to launch this application as a Docker container, the following steps are needed:

* Make sure to have Docker installed on your machine
* Edit the configuration file (conf_dev_conn.json and device_info.json) with your own IP address and provide an updated 'requirements.txt' file, if necessary.
* Run this command, having the shell open in the `device_connector` folder:

    `$ docker build -t device_connector .`

* Then, you are ready to launch the container:

    `$ sudo docker run --name devConn -d -p 8083:8083 device_connector`

* To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

---

## REST API

The device connector only provides the GET method.

The specified URI locates the desired measurement type, while the only valid parameter is `sens`, which must be set to either the sensor name or ID. If the URI is empty, all measurements will be provided (filtered by sensor, if provided).

Measurements are returned as lists of Pythion dictionaries in SenML format (see ***Device agents API - sensors***).

---

## Sensors

### Device agents - sensors

Device agents are implemented as pieces of software (classes) which are instantiated at initialization only if the device uses these objects.
This mechanism is designed to guarantee transparent interoperability between the different possible sensors that can be used.
At the initialization of the device connector, the program will iterate over the list of sensors and initialize the correct device agent, which will be appended to the `self.dev_agents_sens` list. To map the name of the sensor to the positional index within the list, the dict `self.dev_agent_ind_sens` is used (given the *sensor ID*, it returns the correct index of the device agent).

The same dictionary (`dev_agent_ind_sens`) can be used to access the attribute `self.last_meas`.

### Device agents API - sensors

Each device agent (class) related to a sensor *must* have a `measure()` method, which returns the measurement (or *list* of measurements if more than 1 variable can be measured by the same sensor) in SenML format:

    {"n": "Measured quantity", "u": "Unit of meas", "t": timestamp , "v": measured_value}

Whenever the measurement is not carried out (for any kind of issue relative to the sensor), the returned value is `None`. As a consequence the device connector needs to be able to 'discard' these problematic ones and

### Last measurements

The list `self.last_meas` is a list of lists which contains the last measurements for each measured quantity (it is necessary to use a list of lists because the same sensor can measure more than one quantity). It is created by reading the available quantities to be measured inside the lists `measure_type` found in the device information.

`self.last_meas` is actually a list of lists, each of which contains all (last) measurements available from each sensor. The positional indexing reflects that of `self.dev_agents_sens`, meaning the correct measurements can be accessed by making use of `self.device_agent_ind_sens`.

### MQTT topics - sensors

All sensor measurements are published via MQTT on the broker.
The `publishLastMeas()` method performs the publication, acting as follows:

* Iterate through sensor list in the device information dict (`self.whoami`)
* Retrieve the last measurements for each sensor (using the name-index mapping as explained in 'Last measurements')
* Get list of topics associated with the sensor
* For each entry in the selected last-measured list, find the associated topic, knowing the last element in the topic url is the name of the measurement (associated with key `"n"` in the SenML-compliant measure info), **all lowercase and with spaces replaced by underscores**.
* Publish the SenML message containing the measure in the topic

---

## Actuators

### Addressing actuators

The `DevConn` object needs to instantiate one device agent for each actuator. Since the actuator type (model) cannot be known in advance, we need to allow the device connector to be flexible on this.

The proposed solution consists of storing the device agents in the list `dev_agents_act`, by appending them at initialization. To link them to the correct actuator, the dictionary `dev_agent_ind_act` is used. Its keys are the (strings containing the) actuator IDs, and the values are the indices of the corresponding agent within the list `dev_agents_act`. This way, it is possible to map the actuator ID to the correct device agent object.

Notice that this solution is analogous to the one used for the sensors.

### Actuators - device agent API

Each actuator needs to provide a `start()` method and a `stop()` method. Also, it must be able to provide its current state (on/off) via a method `isOn()`, returning True if the state is 'on'.

### Giving commands to actuators

It is possible to perform two operations on the actuators: turn on and turn off (i.e., start and stop). This means that **the complexity needs to be managed outside**, by whoever sends the message to the actuator.

Actuators receive the commands via MQTT at the specified topic. The message need to contain as payload a json-formatted string, with the following format:

    {"cmd": "start/stop", "t": timestamp}

in which the command can be either `"start"` or `"stop"`.

Then, depending on the received command, the `notify()` callback, used by `MyMQTT` will choose the associated actuator and call the corresponding method on it.

---

## Device information JSON file

Here is reported the structure (keys) of the `.json` file containing the device connector information. An example is provided, called `device_info.json`.

* **id**: device ID
* **name**: device name
* **endpoints**: list containing the supported M2M communication protocols
* **endpoints_details**: list containing, for each communication protocol in 'endpoints', the details for the communication (address/topic base name)
* **greenhouse**: ID of the greenhouse associated with the device (raspberry)
* **resources**: list of "resources", i.e., sensors/actuators whose functionalities can be accessed from other parts of the application
  * **sensors**: list of available sensors
    * **id**: sensor ID (unique for each sensor connected to the device)
    * **device_name**: name of the sensor
    * **measure** type: list containing the measured quantities
    * **units**: units of measurement for the specified quantities
    * **device_id**: device to which the sensor is connected
    * **available_services**: list of possible communication protocols through which the measurements can be retrieved
    * **services_details**: list containing additional information for each protocol specified among the available ones (e.g., 'topic': list of MQTT topics)
    * **last_update**: timestamp (YYYY-MM-DD hh:mm:ss) for the last update
  * **actuators**: list of available actuators
    * **id**: actuator ID, unique for each actuator on the same device
    * **device_name**: actuator name
    * **device_id**: id of the device (raspberry) it is connected to
    * **available_services**: list of supported communication protocols for communicating (i.e., giving commands) to the actuator
    * **services_details**: additional information related to the specified communication protocols
* **last_update**: timestamp (YYYY-MM-DD hh:mm:ss) the information was last updated

---

## Device connector configuration file

Here is the structure of the configuration file for the device connector.

* **project_name**: "commercial" name of the project
* **project_owner**: owner(s)/organization name
* **services_catalog**: services catalog (static) information - needed to register at startup
  * **ip**
  * **port**
  * **methods**: supported REST methods
* **device_connector**: information about the device connector needed at setup
  * **id**: device ID
  * **endpoints**: supported M2M communication protocols
  * **endpoints_details**: for each of the previously specified endpoints, the details about the protocol (e.g., IP and port for REST/base name for MQTT)
* **sens_pins**: list of sensors and corresponding pins
  * **id**: sensor ID - corresponding to the one found in the device info JSON file
  * **name**: sensor name
  * *Pins*:
    * If I2C: **dt** (data connection) and **sck** (digital clock connection)
    * Else: **out** - data transmission pin
* **act_pins**: list of actuators and corresponding pins
  * **id**: actuator ID - corresponding to the one found in the device info JSON file
  * **name**: actuator name
  * **out**: digital output pin

---

## Device agents

The following device agents have been provided:

* DHT11: temperature and humidity sensor - [library](https://github.com/adafruit/Adafruit_Python_DHT) ~ DEPRECATED
* BMP180: atmospheric pressure - [library](https://github.com/adafruit/Adafruit_Python_BMP) ~ DEPRECATED (sensor is not made anymore)
* GY-30/BH1750: light sensor - [library](https://github.com/adafruit/Adafruit_CircuitPython_BH1750)

The device agent programs can work even if the required libraries needed for the sensor are not available - in this case, they will work as random number generators.

Each agent was developed in such a way that the program can be ran in standalone mode as a way to test both the presence of the libraries and of the sensor on the current system/venv/container.

---

## API

The device connector provides the following ways to communicate:

* To get the measurements of the sensors, it is needed to subscribe to the corresponding MQTT topics. Since there can be multiple sensors measuring the same quantity (as is the case with temperature), one can choose to either pick one measurement only, or to use MQTT topic wildcards.
The general topic syntax is:

    smartGreenhouse/*device_id*/*sensor_id*/*measured_quantity*

  which means it is possible to subscribe to 'smartGreenhouse/1/*/temperature' in order to get all possible temperature measurements.
* To submit commands to the actuators (water delivery strategy, illumination strategy)), it is needed to publish messages in the topics related to the actuators
