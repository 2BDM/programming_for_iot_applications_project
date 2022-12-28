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

### List of available methods

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
 
## Working principle

When launched, the web service will first (try to) register itself at the provided services catalog. Then it will start operating looking for incoming HTTP requests on the specified port.

Any type oc communication with other application microservices happens through RESTful APIs.

While still listening for incoming requests, the program will perform a timeout check on the catalog records. Therefore it is necessary that all connected devices update their records (by means of PUT requests) every now and then.

The catalog will also have to update its own information at the services catalog. This operation is done continuously, as the records cleanup.











