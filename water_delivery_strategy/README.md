# Water delivery strategy

This folder contains the 'water delivery' microservice for the smart-greenhouse application.

## Task

The main job of this microservice is to monitor the soli moisture in the greenhouse and decide when to activate the irrigation if available.

There is one unique water delivery strategy service, which has to act on all registered devices (having a water actuator).
It is supposed that the user who includes the actuator for watering wants the water delivery strategy to work on his/her greenhouse.
