# Services Catalog

The service catalog for the application.

It provides REST APIs for retrieving, registering and updating service info.
Sample information is stored inside `serv_catalog.json`.

## Contents

The catalog service is based on the ServicesCatalog class.

The required parameters for this class are the catalog input path and the output path (default `"serv_cat_updated.json"`). The starting catalog path should be passed as command line argument when launching the program (the file is user-specific since it may contain sensitive information, like the telegram token).

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
