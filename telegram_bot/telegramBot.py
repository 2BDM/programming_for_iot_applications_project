import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import requests
import time
import cherrypy
from datetime import datetime

class RESTBot:
    exposed = True



    ##################
    # INITIALIZATION #                                                                                      
    ##################
    def __init__(self, conf_dict):
        self.catalogIP = str(conf_dict["services_catalog"]["ip"])+"/"+ str(conf_dict["services_catalog"]["port"])
        self.myIP = str(conf_dict["telegram"]["endpoints_details"][0]["ip"]) +"/"+ str(conf_dict["telegram"]["endpoints_details"][0]["port"])
        #self.tokenBot=requests.get("http://" + self.catalogIP + "/telegram_token").json()["telegramToken"]
        self.tokenBot = "6226505200:AAFJfAUnwZqRHwk8tH5YbNweoKKKYm0Tufk"
        self.bot = telepot.Bot(self.tokenBot)
        self.users = []
        #self.databaseIP = requests.get("http://" + self.catalogIP + "/service?name=mongoDBadptor").json()["IP"]
        self.myDict = {"id" : conf_dict["telegram"]["id"],
                        "name": "telegramBot",
                        "token": self.tokenBot,
                        "ip": conf_dict["telegram"]["endpoints_details"][0]["ip"],
                        "port":conf_dict["telegram"]["endpoints_details"][0]["port"]}
        #requests.post("http://" + self.catalogIP + "/service", json = self.myDict)
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
    


    ########################
    # SEND A LIST OF PLANT #                                                                                      
    ########################
    # Given a list of plant and a user, send to the user the list in the format <plant_name:plant_id>
    def sendPlantList(self, plantListDict, chat_ID):
        plantList = plantListDict["plant_list"]
        if len(plantList)==0:
            self.bot.sendMessage(chat_ID, text="No plant in our database match your requirements.")
        else:
            message = "Here is a list of plants that match your requirements:"
            for current in plantList:
                currentMessage = "\n"+current["name"]+" : "+ str(current["id"])
                message = message+currentMessage
            self.bot.sendMessage(chat_ID, text=message)
    


    ##########################
    # SEND PLANT INFORMATION #                                                                                      
    ##########################
    def sendPlantInformation(self, information, chat_ID):

        message = "Information about the selected plant:\n"
        message = message + "ID: "+str(information["id"])+"\nName: "+str(information["name"])+"\nCategory: "+str(information["category"])
        size = "\nSize range: "+str(information["size"][0])+"-"+str(information["size"][1])
        light = "\nLight range: "+str(information["min_light_lux"])+"-"+str(information["max_light_lux"])
        temperature = "\nTemperature range: "+str(information["min_temp"])+"-"+str(information["max_temp"])
        humidity = "\nHumidity range: "+str(information["min_env_humid"])+"-"+str(information["max_env_humid"])
        soil = "\nSoil moisture range: "+str(information["min_soil_moist"])+"-"+str(information["max_soil_moist"])
        generalInfo = "\n"+ str(information["soil"])+". "+str(information["sunlight"])+". "+str(information["watering"])+". "+str(information["fertilization"])+". "+str(information["pruning"])+".  "+str(information["blooming"])+". "+str(information["color"])+"."
        message = message + size + light + temperature + humidity + soil + generalInfo

        self.bot.sendPhoto(chat_id=chat_ID, photo=str(information["image"]))
        self.bot.sendMessage(chat_ID, text=message)



    ################################
    # MANAGIN THE RECIVED MESSAGES #                                                                                      
    ################################
    def on_chat_message(self, msg):

        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg["text"]
        lines = message.split("\n")
        command = lines[0].replace(" ","")



        #########
        # START #                                                                                      
        #########
        if command == "/start":

            self.bot.sendMessage(chat_ID, text="Hi, welcome to the GreenHouse application.\nHere you will be able to manage your plants \
and your greenhouses. Moreover we will warn you when the water in the tank is low and you should refill it. Here's the list of command \
you can use, if you need information about how to use a command, just write the command itself and press send, you will be given clear \
instructions:\n/addUser\n/addGreenhouse\n/getPlantList\n/getPlantInformation\n/getGraph\n/myInformation")
            
        
            
        ############
        # ADD USER #                                                                                      
        ############
        elif command == "/addUser":

            if len(lines) == 1:

                self.bot.sendMessage(chat_ID, text="To add a user send a message \
with the following format:\n/addUser\n<user_name>\n<user_surname>\n<email_address>")
                
            elif len(lines) == 4:

                myDictionary = {"id": chat_ID, 
                                "user_name": lines[1].replace(" ",""), 
                                "user_surname": lines[2].replace(" ",""), 
                                "email_addr": lines[3].replace(" ",""), 
                                "telegram_id": chat_ID, 
                                "greenhouse": list(), 
                                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

                try:

                    resp = requests.post("http://"+self.catalogIP+"/user", json.dumps(myDictionary))

                    if resp.status_code == 201:

                        self.bot.sendMessage(chat_ID, text='User added correctly!')
                        self.users[chat_ID] = myDictionary

                    elif resp.status_code == 400:

                        self.bot.sendMessage(chat_ID, text='Error, try again.') 

                except:

                    self.bot.sendMessage(chat_ID, text='The server is not responding, please try again later.')

            else: 

                self.bot.sendMessage(chat_ID, text="Wrong format for adding a user. To add a user send a \
message with the following format:\n/addUser\n<user_name>\n<user_surname>\n<email_address>")
                


        ##################
        # ADD GREENHOUSE #                                                                                      
        ##################
        elif command == "/addGreenhouse":

            if len(lines) == 1:

                self.bot.sendMessage(chat_ID, text="To add a greenhouse send a message with the following format:\
\n/addGreenhouse\n<greenhouse_id>\n<plant_id>\nIn order to find the right ID plant, use the command /getPlantList.")

            elif len(lines) == 3:

                plantID = lines[2]
                try:
                    needs = requests.get("http://" + self.databaseIP + "?coll=plants&id="+plantID+"needs=1").json()["needs"]
                    myDictionary = {"id": lines[1].replace(" ",""),  
                                    "user_id": chat_ID,
                                    "plant_type": lines[2].replace(" ",""),
                                    "plant_needs": needs}
                    
                    try:

                        resp = requests.post("http://" + self.catalogIP + "/greenhouse", json.dumps(myDictionary)) 

                        if resp.status_code == 201:

                            self.bot.sendMessage(chat_ID, text='GreenHouse added correctly!')

                        elif resp.status_code == 400:

                            self.bot.sendMessage(chat_ID, text='Error, try again.') 
                    
                    except:
                        self.bot.sendMessage(chat_ID, text='The server is not responding, please try again later.')

                except:

                    self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

            else:

                self.bot.sendMessage(chat_ID, text="Wrong format for adding a greenhouse. To add a greenhouse send a message with the \
following format:\n/addGreenhouse\n<greenhouse_id>\n<plant_id>\n")
                


        ##################
        # GET PLANT LIST #                                                                                      
        ##################        
        elif command == "/getPlantList":

            if len(lines) == 1:

                self.bot.sendMessage(chat_ID, text="To get a list of plants that suits your needs, \
send a message with one of the following formats:\n- To get plants within a certain size range send:\n/getPlantList\nminSize:<value>\n\
maxSize:<value>\n- To get plants that belong to a certain category send:\n/getPlantList\ncategory:<value>\n- To get plants that are able \
to stain at a certain temperature send:\n/getPlantList\ntemperature:<value>\n- To get plants that need a certain humidity send:\n\
/getPlantList\nhumidity:<value>\n- To get plants that need a certain amount of light send:\n/getPlantList\nlux:<value>\n\
- To get plants that can stay in a soil with a certain moisture send:\n/getPlantList\nmoisture:<value>\n")
            
            elif len(lines) == 2:

                parameter = lines[1].split(":")[0].replace(" ","")
                value = lines[1].split(":")[1].replace(" ","")

                if parameter == "category":
                    
                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&categoty="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)

                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                elif parameter == "temperature":

                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&temperature="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "humidity":
                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&humidity="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "lux":
                    
                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&lux="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "moisture":
                    
                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&moisture="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                else:

                    self.bot.sendMessage(chat_ID, text="Wrong format for searching plants. To get a list of plants that suits your needs, \
send a message with one of the following formats:\n- To get plants within a certain size range send:\n/getPlantList\nminSize:<value>\n\
maxSize:<value>\n- To get plants that belong to a certain category send:\n/getPlantList\ncategory:<value>\n- To get plants that are able \
to stain at a certain temperature send:\n/getPlantList\ntemperature:<value>\n- To get plants that need a certain humidity send:\n\
/getPlantList\nhumidity:<value>\n- To get plants that need a certain amount of light send:\n/getPlantList\nlux:<value>\n\
- To get plants that can stay in a soil with a certain moisture send:\n/getPlantList\nmoisture:<value>\n")
            elif len(lines) == 3:

                parameter1 = lines[1].split(":")[0].replace(" ","")
                value1 = lines[1].split(":")[1].replace(" ","")
                parameter2 = lines[2].split(":")[0].replace(" ","")
                value2 = lines[2].split(":")[1].replace(" ","")

                if parameter1 == "minSize" and parameter2 == "maxSize":

                    try:
                        plantList = requests.get("http://" + self.databaseIP + "?coll=plants&min_size="+value1+"&max_size="+value2+"&N=5").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")
                
                else:
                    self.bot.sendMessage(chat_ID, text="Wrong format for searching plants. To get a list of plants that suits your needs, \
send a message with one of the following formats:\n- To get plants within a certain size range send:\n/getPlantList\nminSize:<value>\n\
maxSize:<value>\n- To get plants that belong to a certain category send:\n/getPlantList\ncategory:<value>\n- To get plants that are able \
to stain at a certain temperature send:\n/getPlantList\ntemperature:<value>\n- To get plants that need a certain humidity send:\n\
/getPlantList\nhumidity:<value>\n- To get plants that need a certain amount of light send:\n/getPlantList\nlux:<value>\n\
- To get plants that can stay in a soil with a certain moisture send:\n/getPlantList\nmoisture:<value>\n")

            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for searching plants. To get a list of plants that suits your needs, \
send a message with one of the following formats:\n- To get plants within a certain size range send:\n/getPlantList\nminSize:<value>\n\
maxSize:<value>\n- To get plants that belong to a certain category send:\n/getPlantList\ncategory:<value>\n- To get plants that are able \
to stain at a certain temperature send:\n/getPlantList\ntemperature:<value>\n- To get plants that need a certain humidity send:\n\
/getPlantList\nhumidity:<value>\n- To get plants that need a certain amount of light send:\n/getPlantList\nlux:<value>\n\
- To get plants that can stay in a soil with a certain moisture send:\n/getPlantList\nmoisture:<value>\n")


        
        #########################
        # GET PLANT INFORMATION #                                                                                      
        #########################
        elif command == "/getPlantInformation":

            if len(lines) == 1:
                self.bot.sendMessage(chat_ID, text="To get the informations about a plant, send a message with the following format: \
\n/getPlantInformation\n<plant_id>")
                
            elif len(lines) == 2:

                plantID = lines[1].replace(" ","")

                try:
                    info = requests.get("http://" + self.databaseIP + "?coll=plants&id="+plantID).json()
                    self.sendPlantInformation(info, chat_ID)
                except:
                    self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for getting plant information. To get a plant information \
send a message with thefollowing format:\n/getPlantInformation\n<plant_id>")



        #############
        # GET GRAPH #                                                                                      
        #############
        elif command == "/getGraph":

            if len(lines) == 1:

                pass

            elif len(lines) == 2:

                pass

            else:

                pass



        ######################
        # GET MY INFORMATION #                                                                                      
        ######################
        elif command == "/myInformation":

            try:
                resp = requests.get("http://"+self.catalogIP+"/user?id="+str(chat_ID)).json()
                info = resp.json()
                if resp.status_code == 201:
                    message = "Your user profile has the following informations:\n"
                    information = "- ID: "+str(info["id"])+"\nUser name: "+str(info["user_name"])+"\nUser surname: "+str(info["user_surname"])+"\nEmail address: "+str(info["email_addr"])+"\nGreenhouse list:\n"
                    message = message + information
                    greenhouseList = info["greenhouse"]

                    if len(greenhouseList)==0:
                        currentMessage = "\nCurrently you have no greenhouse registered to the service."
                        message = message + currentMessage

                    else:
                        for gh in greenhouseList:
                            current = requests.get("http://"+self.catalogIP+"/greenhouse?id="+str(gh)).json()
                            currentMessage = "\nGreenhouse: "+str(gh)+"\nPlant: "+current["plant_type"]+"\nPlant ID: "+current["plant_id"]+"\n"
                            message = message + currentMessage
                    
                    self.bot.sendMessage(chat_ID, text=message)
                    
                else:
                    self.bot.sendMessage(chat_ID, text="You have to create a user before getting your own informations.")


            except:
                self.bot.sendMessage(chat_ID, text="Server is not responding")



        ####################
        # IN CASE OF ERROR #                                                                                      
        ####################
        else:

            self.bot.sendMessage(chat_ID, text="The command you sent is not in our list. Check again the list of possible commands. \
\n/addUser\n/addGreenhouse\n/getPlantList")
            
    

    ########
    # POST #                                                                                      
    ########
    def POST(self, *uri, **param):
        
        greenhouseID = param["greenhouseID"]
        try:
            resp = requests.get("http://"+self.catalogIP+"/greenhouse?id="+greenhouseID)
            chat_ID = resp["user_id"]
            self.bot.sendMessage(chat_ID, text="The water in the tank of one of your greenhouse is low. You should refill it. The greenhouse \
ID is "+ greenhouseID)
        except:
            raise cherrypy.HTTPError(400, "Unable to contact the user as the services catalog is not responding") 


        


########
# MAIN #                                                                                      
########
if __name__ == "__main__":
    conf_dict = json.load(open("settings.json"))
    cherryConf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': conf_dict["telegram"]["endpoints_details"][0]["ip"], 'server.socket_port': conf_dict["telegram"]["endpoints_details"][0]["port"]})
    bot = RESTBot(conf_dict)
    cherrypy.tree.mount(bot, '/', cherryConf)
    cherrypy.engine.start()
    cherrypy.engine.block()