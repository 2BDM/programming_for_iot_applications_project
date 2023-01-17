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

* project_name
* project_owner
* services_catalog
  * ip
  * port
  * methods (list)
* broker
  * ip
  * port
* telegram
  * telegram_token
* device_catalog
  * ip
  * port
  * methods (list)
  * last_update
* users (list)
  * id
  * user_name
  * user_surname
  * email_addr
  * telegram_id (?)
  * greenhouse
  * last_update
* greenhouses
  * id
  * user_id
  * device_id
  * plant_id
  * plant_type
  * plant_needs (list)
    * ... (need to specify what kind of measurements - TODO)
  * last_update
* services
  * name
  * endpoints
  * endpoints_details
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
