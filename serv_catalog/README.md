# Services Catalog

The service catalog for the application.

It provides REST APIs for retrieving, registering and updating service info.
Information is stored inside `serv_catalog.json`.

## Contents

### **Catalog syntax**

* project_name
* project_owner
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
  * plant_id
  * plant_type
  * plant_needs (list)
    * ... (need to specify what kind of measurements)
  * last_update

### **Timestamp syntax**

The timestamps  (`last_update`) will have the following syntax:

    %Y-%m-%d %H:%M:%S
