# Telegram Bot

It is the main interface of the user with the application.
It provides functions to register users, manage greenhouses, obtaining informations about the available plants and requesting plots showing the data collected from the system.

The bot is built in a resilient way: if for some reason it crashes, it is possible to restart it and retrieve the old information of users and greenhouses which was previously registered on the services catalog.

**Important notice**: the telegram bot uses a key which is private and it has been requested via the BotFather (@BotFather on Telegram) service. Once the key is received, you will also get the telegram link for your own bot. For obvious reasons, the key is not present in the services catalog available in this repository, as it needs to be added manually. If the key is missing, the bot will not start.

## Launching the container

In order to launch this application as a Docker container, the following steps are needed:

- Make sure to have Docker installed on your machine
- Edit the configuration file (settings.json) with your own IP address and make sure the telegram bot key and link are updated in the services catalog.
- Run this command, having the shell open in the `telegram_bot` folder:

    `$ docker build -t telegram_bot .`

- Then, you are ready to launch the container:

    `$ sudo docker run --name telegramBot -d -p 9090:9090 telegram_bot`

- To check that it is working, run:

    `$ docker ps`
  
  you should see the container you just created.

## Functions

The available functions, from the user side, are:

- /addUser
- /addGreenhouse
- /getPlantList
- /getPlantInformation
- /getGraph
- /myInformation
