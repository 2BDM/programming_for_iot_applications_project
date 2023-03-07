# Device Catalog

The device catalog for the application.

It provides a REST API for retrieving, registering and updating devices info. In the case of this application, devices consist of Raspberry Pi's, provided with a series of sensors.
The advertised information will be that of all available interfaces, sensors and measurements for each Raspberry.

Sample information can be found inside `dev_catalog.json`.

## Contents

The catalog web service is built on top of the DeviceCatalog class.

The constructor of this class requires:

* The path for the input catalog (if invalid, the default one will be provided)
* The path to the updated catalog (saved everytime the saveAsJson() method is called - typically after any catalog update)

### Launching the container

In order to launch this application as a Docker container, the following steps are needed:

* Make sure to have Docker installed on your machine
* Edit the configuration file (dev_catalog.json) with your own IP address.
* Run this command, having the shell open in the `dev_catalog` folder:

    `$ docker build -t dev_catalog .`

* Then, you are ready to launch the container:

    `$ sudo docker run --name devCatalog -d -p 8082:8082 dev_catalog`

* To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

### List of available methods

Below is a list of methods for the DeviceCatalog class. Notice that this is not the class used as web service.

* *saveAsJson*: stores the current catalog as a JSON file at the specified location (given at instantiation)

#### **Getters**

* getDevCatInfo
* getDevices

#### **Counters**

* countDevices

#### **Searchers**

* searchDevice

#### **Adders**

* addDevice

#### **Updaters**

* updateDevice

#### **Cleaners**

* cleanDevices

### Catalog Structure

The following is the structure of the device catalog JSON file

* project_name
* project_owner
* device_catalog
  * ip
  * port
  * methods (list)
* devices (list)
  * id
  * name
  * endpoints (list)
  * endpoints_details (list)
    * endpoint
    * address (if REST)
    * topic (list) (if MQTT)
  * greenhouse
  * resources (dict)
    * sensors (list)
      * id
      * device_name
      * measure_type (list)
      * units
      * device_id
      * available_services (list)
      * services_details (list)
        * service_type
        * address (if REST)
        * topic (list) (if MQTT)
      * last_update
  * last_update
* last_update

### **Timestamp syntax**

The timestamps (`last_update`) follow this syntax:

    %Y-%m-%d %H:%M:%S

## Device Catalog - Web service

The DeviceCatalog class is used to create the web service which is used to allow device registration.

### REST methods

If the path is not specified, the program will return a list of supported operations.

#### GET

If found, response code is 200, if not, 404 and if wrong parameters are passed in the URI, the code is 400.

* `/devices`: return the full list containing all registered devices
* `/device?id=...`: return the device given the specified ID, if found.
* `/device?name=...`: return the device given the specified name, if found.
* `/new_id`: returns a json containing as only element 'id', associated with the next available ID

#### POST

Method used to add new devices (not previously registered).
The response code is 201 if the device was correctly added, else it is 400 (for any reason - may be that the device already exists).

* `/device` + json in body: used to add a new device.

#### PUT

Method used to update devices (must be previously registered).
The response code is 200 if the device was correctly updated, else it is 400 (for any reason - may be that the device has not already been added).

* `/device` + json in body: used to update a new device.

### Other methods

The following methods are used in general to perform the operations which the catalog needs to do without being triggered by a HTTP request.

* `cleanRecords`: performs cleanup, by deleting devices older than the timeout (120s, by default). It prints on the standard output the number of devices it removes everytime it is called, if the number is > 0.
* `registerAtServiceCatalog`: performs registration at the service catalog. It returns 1 if the registration was successful, -1 if the information was already present (**an update is performed** by means of `updateServiceCatalog`) or 0 if it was not possible to add the information (server is unreachable).
* `updateServiceCatalog`: it is used to perform a PUT request on the service catalog to update the information. It returns 1 if the update was successful, -1 if it was needed to register (useful if the device catalog crashes and it is needed to register again) or 0 if it was not possible to reach the service catalog server.
* `startOperation`: used to launch the loop for the operation of the device catalog. Periodically (every 'refresh_rate') the program cleans the records and updates its info at the device catalog.
* `getMyIP`: used to retrieve its own IP address.
* `getMyPort`: used to retrieve its own port number.

## Working principle

When launched, the web service will first (try to) register itself at the provided services catalog. Then it will start operating looking for incoming HTTP requests on the specified port.

Any type of communication with other application microservices happens through RESTful APIs.

While still listening for incoming requests, the program will perform a timeout check on the catalog records. Therefore it is necessary that all connected devices update their records (by means of PUT requests) every now and then.

The catalog will also have to update its own information at the services catalog. This operation is done continuously, as the records cleanup.
