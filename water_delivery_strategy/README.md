# Water delivery strategy

This folder contains the 'water delivery' microservice for the smart-greenhouse application.

## Launching the container

In order to launch this application as a Docker container, the following steps are needed:

- Make sure to have Docker installed on your machine
- Edit the configuration file (water_conf.json) with your own IP address.
- Run this command, having the shell open in the `water_delivery_strategy` folder:

    `$ docker build -t water_delivery .`

- Then, you are ready to launch the container:

    `$ sudo docker run --name waterDelivery -d -p 8089:8089 water_delivery`

- To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

## Task

The main job of this microservice is to monitor the soli moisture in the greenhouse and decide when to activate the irrigation if available.

There is one unique water delivery strategy service, which has to act on all registered devices (having a water actuator).
It is supposed that the user who includes the actuator for watering wants the water delivery strategy to work on his/her greenhouse.
