# Programming for IoT applications project

Project for the course Programming for IoT Applications at Politecnico di Torino, academic year 2022-2023.

The project consists in the implementation of an application used to monitor and control smart greenhouses, based on the microservices programming paradigm. The system allows users to tailor the service based on the specific plant used and at the same time constantly monitor the environment, all by interfacing via a Telegram bot.

## Application structure

This applcation is developed as a collection of small, independent services (microservices), which communicate to exchange information used for the different functions.
This means each component of this application is fully self contained and communicates by means of specific APIs, which are known and based on machine-to-machine communication protocols. As a result, the application is fully modular.

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

Once that has been done, it is enough to instantiate and run the Docker containers. If the IP addresses have been correctly set and the different containers run in the same network, the application will be launched. The application has been built in such a way that the order of launch of the containers does not matter.

Inside each README file there are the detailed instructions on how to launch the containers (terminal commands).
