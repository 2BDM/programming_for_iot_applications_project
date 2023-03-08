# Programming for IoT applications project - Greenhouse 101

![Python Version](https://img.shields.io/badge/python-3.8%20|%203.10-informational?style=flat&logo=python&logoColor=white)
![GitHub](https://img.shields.io/github/contributors/iotprojectMPEG/mainproject?style=flat&logo=github)
![GitHub](https://img.shields.io/github/license/iotprojectMPEG/mainproject?style=flat)

Project for the course Programming for IoT Applications at Politecnico di Torino, academic year 2022-2023.

![ICT4SS_logo](/img/ict4ss_logo.jpg "Ict for Smart Societies")

Greenhouse 101 is an application used to monitor and control smart greenhouses, based on the microservices programming paradigm. The system allows users to tailor the service based on the specific plant used and at the same time constantly monitor the environment, all by interfacing via a Telegram bot.

The purpose of this project is to provide an automated way to look after plants inside a greenhouse, while making sure resources, such as water, does not go wasted. The user will be guided by a Telegram bot, through which he/she will be able to manage the greenhouse(s) and be notified about its condition.

The application is able to tailor the plant needs by retrieving information stored in a database.

<img src="img/youtube.svg" width="80">

A promo video and a demo are available on YouTube:

* [Promo](https://youtu.be/0MKoJqTkVQ4)
* [Demo](https://youtu.be/5EUWtzwSwGE)

## Application structure

This applcation is developed as a collection of small, independent services (microservices), which communicate to exchange information used for the different functions.
This means each component of this application is fully self contained and communicates by means of specific APIs, which are known and based on machine-to-machine communication protocols. As a result, the application is fully modular.

<img src="img/app_architecture.svg">

The main components of the application are:

* **Services catalog**: it is the service registry system for the application. Its endpoints are known by all other elements, as it is a static service used by the microservices to advertise their information and to obtain the info about other components. It is based on a JSON file, which is constantly updated/cleaned and is saved locally to prevent that crasher could cause information losses.
* **MQTT broker**: it is the central element in MQTT transmissions, through which the messages can be delivered. In this application, a public MQTT broker was used, whose information is stored in advance on the services catalog. It is possible to use any kind of MQTT broker provided that its information is correctly advertised on the services catalog.
* **Device catalog**: it is the device registry system on which each device connector can post its information. This information is then used by other components, in particular the weather station and the strategies, to obtain the APIs for communication with the devices. It is based on a JSON file, which is constantly updated.
* **Device connector** (1 for each greenhouse): it is the program which runs on every single Raspberry Pi which is added to the application. It is responsible for initializing the 'device agents' which allow it to access the functionalities of sensors and actuators.
  * **Device Agents**: they are the software elements which abstract the complexity of having to handle different sensors/actuators. They are implemented as Python classes providing common APIs, which guarantee the same procedures to perform the same functions on any device.
* **Telegram bot**: it is the main point of interface with the user for this application. The bot is an automated communication channel through which clients can register and add their device(s) to the system. It is responsible of providing monitoring on the system, also via data representation.
* **Weather station**: it is a microservice exploiting measurements coming from the different sensors to provide both an estimate for the current weather and, most notably, the estimate for precipitations in the following days. It also groups the received data and transmits daily recaps (average values) to MongoDB.
* **Water delivery strategy**: it is the microservice which controls the irrigation system. It reads the measurements done by the moisture sensors and then it decides whether to turn on the irrigation system, also depending on the specific plants needs. The water is taken from a tank, which can be placed on load cells to monitor its weight and notify the user when it is empty. The information from the weather station is also used to suggest the days in which the tank could be filled with rainwater.
* **Artificial lighting strategy**: it is the microservice used to control the artificial lighting system, based on the illumination system and on the plants needs.
* **Mongo DB**: it is the database system used in the application. It is used to store the plants database, from which the user can select his/her own plant to tailor the service on.
* **Mongo DB adaptor**: it is an application component used to exchange data with the MongoDB database. It also allows for retrieving data visualizations.

## Launching the application

Thanks to their nature, microservices are well-suited to be containerized and executed on any machine running Docker. For this reason, it is possible to create containers for each of the aforementioned components (excluded the message broker), as each subfolder of this repository includes a Dockerfile.
It is first required, however, that the configuration files of each microservice are reviewed and updated, as they need to include the IP address of the machine on which they are running.

Once that has been done, it is enough to instantiate and run the Docker containers. If the IP addresses have been correctly set and the different containers run in the same subnetwork, the application will be launched. The application has been built in such a way that the order of launch of the containers does not matter.

Inside each README file there are the detailed instructions on how to create the containers (terminal commands).

(For reference, take a look here [here](https://docs.docker.com/get-started/))

### Default port numbers

Here are reported the default port numbers for the application microservices:

* Services catalog: 8081
* Device catalog: 8082
* Device connector: 8083
* MongoDB: 8282
* Telegram bot: 9090
* Weather station: 8084
* Lighting strategy: 8088
* Water delivery strategy: 8089

## Application use case

<img src="img/telegram_logo.svg" width="100">

Having launched the application infrastructure, and possibly having connected new devices, we are ready to start using the application.

Users can register via the telegram bot which is found at [this address](http://t.me/IoT_project_group17_bot) - notice that this  bot is connected to a specific telegram token, which is not available in this repository.

The bot will provide the user a series of available commands:

* /addUser: use this command to register as a new user. Need to provide a name, surname and email address. Each user profile is associated with the telegram user.
* /addGreenhouse: use this command to register a new greenhouse for your profile and link a new device. It is needed to provide the device ID (which will become the new greenhouse ID) - an unique identifier - and the plant ID, related to which plant you want to include.
* /getPlantList: this command allows to retrieve a list of plants which satisfy some criteria.
  * minSize/maxSize: get plants in a certain size range
  * category: get plants of a specific category
  * temperature: get plants based on the tolerated temperature
  * humidity: get plants based on typical humidity values
  * lux: get plants based on the required illumination
  * moisture: get plants based on water needs
* /getPlantInformation: use this command to get the complete information about a specific plant given its ID. The response message also includes a photograph.
* /getGraph: obtain a link to the data visualization dashboard provided by MongoDB. The plots refer to weather data provided daily by the weather station (min/max/mean temperature, mean pressure, mean humidity and precipitations).
* /myInformation: print out the information about the user. This command also shows a list of the registered greenhouses with their ID and plants.
