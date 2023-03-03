# Weather station and forecasting

This subfolder contains the programs used for the weather station and for weather forecasting.

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
