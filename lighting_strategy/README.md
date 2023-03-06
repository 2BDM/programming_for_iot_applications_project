# Lighting strategy

This folder contains the 'lighting strategy' microservice for the smart-greenhouse application.

## Task

The main job of this microservice is to monitor the illumination of the greenhouse and decide when to activate the artificial lighting if available.

There is one unique lighting strategy service, which has to act on all registered devices (having a 'lighting strategy' actuator).
It is supposed that the user who includes the actuator for the artificial lighting wants the lighting strategy to work on his/her greenhouse.
