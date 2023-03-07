# Weather station and forecasting

This subfolder contains the programs used for the weather station and for weather forecasting.

## Launching the container

In order to launch this application as a Docker container, the following steps are needed:

- Make sure to have Docker installed on your machine
- Edit the configuration file (weather_station_conf.json) with your own IP address.
- Run this command, having the shell open in the `weather` folder:

    `$ docker build -t weather_station .`

- Then, you are ready to launch the container:

    `$ sudo docker run --name weatherStation -d -p 8084:8084 weather_station`

- To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

---

## Weather station

It is a microservice for the application which is able to read data from the sensors and provide the user (via Telegram) the current weather. Additionally, it will call the weather prediction strategy to retrieve weather (rain) forecasting.

### HTTP requests

The weather station only supports GET requests used to retrieve the weather (either the current one based on the last 2 hour measurements, or the next day precipitations given the last 24h measurements).

#### GET

Possible paths (and parameters):

- `/curr_weather`: retrieve a string containing the estimate of the current weather (sun, rain, clear - at night only, clouds - at daytime only). The used measurements come from the first available sensors'
- `/curr_weather?id=`:
- `/will_it_rain`:
- `/will_it_rain?id=`:
