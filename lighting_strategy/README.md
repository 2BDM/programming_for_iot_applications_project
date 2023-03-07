# Lighting strategy

This folder contains the 'lighting strategy' microservice for the smart-greenhouse application.

## Task

The main job of this microservice is to monitor the illumination of the greenhouse and decide when to activate the artificial lighting if available.

There is one unique lighting strategy service, which has to act on all registered devices (having a 'lighting strategy' actuator).
It is supposed that the user who includes the actuator for the artificial lighting wants the lighting strategy to work on his/her greenhouse.

## Launching the container

In order to launch this application as a Docker container, the following steps are needed:

* Make sure to have Docker installed on your machine
* Edit the configuration file (light_conf.json) with your own IP address.
* Run this command, having the shell open in the `lighting_strategy` folder:

    `$ docker build -t lighting_strategy .`

* Then, you are ready to launch the container:

    `$ sudo docker run --name lightStrategy -d -p 8088:8088 lighting_strategy`

* To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.
