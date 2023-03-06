# MongoDB adaptor
The subfolder contains the program and the REST interface to manage the operations on MongoDB.
### MongoDB database
The database is called 2BDM and contains two collections:
- "plants": contains 2759 plants and for each one the following information are provided:
	- _id					
	- name
	- image
	- origin
	- category
	- blooming
	- color
	- size
	- Array
	- soil
	- sunlight
	- watering
	- fertilization
	- pruning
	- max_light_lux
	- min_light_lux
	- max_temp
	- min_temp
	- max_env_humid
	- min_env_humid
	- max_soil_moist
	- min_soil_moist
- "weather": contains all the records computed by the weather_prediction strategy and it is used to maintain an history of the relevations. The following information are provided:
	- _id
	- TMEDIA °C
	- TMIN °C
	- TMAX °C
	- UMIDITA %
	- PRESSIONESLM mb
	- STAGIONE
	- FENOMENI: contains value 0/1 if precipitations are present or not
	- timestamp
### MongoDB charts
It gives the possibility to retrieve some graphs showing historical statistics.
### HTTP requests
The mongoDB adaptor supports the GET and POST operations.
#### GET
- ?coll=plats&id=...&needs=1 --> to have the list of needs of a plant (given ID) 
- ?coll=plats&id=... --> to search by id (retrieves all information) 
- ?coll=plats&name=... --> to search by name (retrieves all information)
- ?coll=plats&min_size=...&max_size=...&N=... --> to search by size 
- ?coll=plats&category=...&N=... --> to search by category   
- ?coll=plats&temperature=...&N=... --> to search by temperature 
- ?coll=plats&humidity=...&N=... --> to search by value of humidity
- ?coll=plats&lux=...&N=... --> to search by the value of light
- ?coll=plats&moisture=...&N=... --> to search by moisture  


- ?coll=weather&date=... --> to search by a specific date
- ?coll=weather&min_date=...&max_date=... --> to search records in a interval of dates
- ?coll=weather&chart_temp=1 --> to have the chart of min, max and mean temperature
- ?coll=weather&chart_prec=1 --> to have the chart of precipitations

All the requests (except for the ID and name) return N records of type [{"_id":id},{"name":name}] and not the full information. So, you should make two requests. 

#### POST
It is provided to insert a new record in the collection "weather"

