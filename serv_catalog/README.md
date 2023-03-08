# Services Catalog

The service catalog for the application.

It provides REST APIs for retrieving, registering and updating service info.
Sample information is stored inside `serv_catalog.json`.

## Contents

The catalog service is based on the ServicesCatalog class.

The required parameters for this class are the catalog input path and the output path (default `"serv_cat_updated.json"`). The starting catalog path should be passed as command line argument when launching the program (the file is user-specific since it may contain sensitive information, like the telegram token).

### Launching the container

In order to launch this application as a Docker container, the following steps are needed:

* Make sure to have Docker installed on your machine
* Edit the configuration file (serv_catalog.json) with your own IP address nd make sure all other informations (Telegram and MQTT broker) are updated.
* Run this command, having the shell open in the `serv_catalog` folder:

    `$ docker build -t serv_catalog .`

* Then, you are ready to launch the container:

    `$ sudo docker run --name servCatalog -d -p 8081:8081 serv_catalog`

* To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

### List of available methods

This is  list of all methods defined for the ServicesCatalog class.

* **saveAsJson**: stores the current catalog as json file on the specified output path

#### ***Getters***

* getProjectName
* getProjectOwner
* getBroker
* getTelegram
* getDevCatalog
* getUsers
* getGreenhouses
* getServices

#### ***Counters***

* countUsers
* countGreenhouses
* countService

#### ***Searches***

* searchUser
* searchGreenhouse
* searchService

#### ***Adders***

* addDevCat
* addUser
* addGreenhouse
* addService

#### ***Updaters***

* updateDevCat
* updateUser
* updateGreenhouse
* updateService

#### ***Cleaners***

* cleanDevCat
* cleanUsers
* cleanGreenhouses
* cleanServices

### **Catalog syntax**

The following is the structure of the catalog JSON file:

* project_name: name of the project
* project_owner: owner(s)/organization
* services_catalog: information about the services catalog (this element needs to be known by all microservices/entities in the application - hard-coded)
  * ip
  * port
  * methods: list of supported REST methods
* broker: information about the MQTT broker
  * ip
  * port
* telegram: information about the telegram bot
  * telegram_token
* device_catalog: informations about the device catalog (endpoints)
  * ip
  * port
  * methods: list of supported REST methods
  * last_update: timestamp of last update
* users: list of users with information
  * id: **unique** identifier
  * user_name: name of the user
  * user_surname: surname of the user
  * email_addr: email address of the user
  * telegram_id: telegram name associated to the user (*to be reviewed*)
  * greenhouse: list of the identifiers of the greenhouses (**can be more than one**)
  * last_update
* greenhouses: greenhouse information
  * id: greenhouse ID (**different from user ID**)
  * user_id: associated user ID
  * device_id: ID of the associated device (Raspberry PI) - one for each greenhouse
  * plant_id: ID of the plant (one for each greenhouse) - used for customizing strategies
  * plant_type: name of the plant
  * plant_needs (list)
    * ... (need to specify what kind of measurements - TODO)
  * last_update
* services: list of available services
  * name: name of the service
  * endpoints: list of supported M2M communication protocols
  * endpoints_details: details about the protocols
    * endpoint
    * IF REST: address
    * IF MQTT: topic

### **Timestamp syntax**

The timestamps  (`last_update`) will have the following syntax:

    %Y-%m-%d %H:%M:%S

## Working principle

The service catalog is a web service which is used to provide to every application component (microservice) information about others.

The web service exploits a RESTful API.

Additionally, every 30 seconds, the program performs a check on its records to delete elements older than 2 minutes.

## Response codes

Below are listed the **possible HTTP response codes** associated with each request.

* GET:
  * 200: object was correctly found and returned
  * 400: missing parameters (for '*conditionsal*' get requests, e.g., searches)
  * 404: object not found (parameter(s) pointed to a missing location)
* POST:
  * 201: element was added successfully
  * 400: unable to add element
* PUT:
  * 200: successful update
  * 400: unable to update element

Whenever other status code are returned, especially in the case of 500, it means it was not possible to reach the server/*other things* went wrong.

---

## Requests

These are the possible request formats.

### GET

If the element is not found, error code 404. If the parameter is wrong (when searching by ID or name), the code is 400.

* `/project_info`: returns the string containing the name of the project and the owner.
* `/broker`: get the json containing the broker information.
* `/telegram`: get the json containing the Telegram information.
* `/device_catalog`: get the json containing the device catalog information.
* `/users`: get full list of user jsons.
* `/user?id=...`: get the information about the user given the ID.
* `/greenhouses`: get full list of greenhouses jsons.
* `/greenhouse?id=...`: get greenhouse, having specified the ID.
* `/services`: get list of services.
* `/service?id=...`: get service, specified the ID.
* `/service?name=...`:  get service, specified the name (all lowercases and ' ' replaced by '_')
* `/new_user_id`: return the ID for a new user registering
* `/new_greenhouse_id`: return the ID for a new greenhouse registering
* `/new_serv_id`: return the ID for a new service registering

If nothing else is specified, then a list of commands is specified.

### POST

If the post was successful (was able to create record), the code is 201, if it was not possible to add the record, the code is 400 (it can mean that the record already exists).

When adding jsons, the program checks for all the fields to be present.

* `/device_catalog` + json in body: add device catalog info.
* `/user` + json in body: add user info.
* `/greenhouse` + json in body: add greenhouse info.
* `/service` + json in body: add service information.

### PUT

If the update is successful, the response code is 200, else, the code is 400.

* `/device_catalog` + json in body: update device catalog info.
* `/user` + json in body: update user info.
* `/greenhouse` + json in body: update greenhouse info.
* `/service` + json in body: update service information.

---

## Additional information

For some useful methods to register at the service catalog/update information, look at the Device Catalog and Device Connector code.
