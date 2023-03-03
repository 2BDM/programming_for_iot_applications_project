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

    def __init__(self, token):
        self.catalogIP = 0
        #self.catalogIP = json.loads(open("initialization"))["catalogIP"]
        #self.myIP = json.loads(open("initialization"))["IP"]
        self.myIP = 0
        #self.tokenBot=requests.get("http://" + self.catalogIP + "/telegram_token").json()["telegramToken"]
        self.tokenBot = "6226505200:AAFJfAUnwZqRHwk8tH5YbNweoKKKYm0Tufk"
        self.bot = telepot.Bot(self.tokenBot)
        self.users = []
        #self.databaseIP = requests.get("http://" + self.catalogIP + "/service?name=mongoDBadptor").json()["IP"]
        self.myDict = {"id" : 123456,
                        "name": "telegramBot",
                        "token": self.tokenBot,
                        "IP": self.myIP}
        #requests.post("http://" + self.catalogIP + "/service", json = self.myDict)
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
        self.greenhouseCount = 0


    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)

        message = msg["text"]
        lines = message.split("\n")
        command = lines[0].replace(" ","")



        if command == "/start":
            self.bot.sendMessage(chat_ID, text="Hi, welcome to the GreenHouse application.\nHere you will be able to manage your plants \
and your greenhouses. Moreover we will warn you when the water in the tank is low and you should refill it. Here's the list of command \
you can use, if you need information about how to use a command, just write the command itself and press send, you will be given clear \
instructions:\n/addUser\n/addGreenhouse\n/getPlantList")



        elif command == "/addUser":
            if len(lines) == 1:
                self.bot.sendMessage(chat_ID, text="To add a user send a message\
 with the following format:\n/addUser\n<user_name>\n<user_surname>\n<email_address>")
            elif len(lines) == 4:
                myDictionary = {"id": chat_ID, 
                                "user_name": lines[1].replace(" ",""), 
                                "user_surname": lines[2].replace(" ",""), 
                                "email_addr": lines[3].replace(" ",""), 
                                "telegram_id": chat_ID, 
                                "greenhouse": list(), 
                                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                resp = requests.post("http://"+self.catalogIP+"/user", json = myDictionary)  
                if resp.status_code == 200:
                    self.bot.sendMessage(chat_ID, text='User added correctly!')
                    self.users[chat_ID] = myDictionary
                else:
                    self.bot.sendMessage(chat_ID, text='Error, try again.') 

            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for adding a user. To add a user send a\
 message with the following format:\n/addUser\n<user_name>\n<user_surname>\n<email_address>")
                

        
        elif command == "/addGreenhouse":
            if len(lines) == 1:
                self.bot.sendMessage(chat_ID, text="To add a greenhouse send a message with the following format:\
\n/addGreenhouse\n<greenhouse_id>\n<plant_id>\nIn order to find the right ID plant, use the command /getPlantList.")

            elif len(lines) == 3:
                plantID = lines[2]
                needs = requests.get("http://" + self.databaseIP + "?coll=plants&id="+plantID).json()
                myDictionary = {"id": self.greenhouseCount, 
                                "name": lines[1], 
                                "plantID": lines[2],
                                "plantNeeds": needs}
                resp = requests.post("http://" + self.catalogIP + "/greenhouse", json = myDictionary) 

                if resp.status_code == 200:
                    self.bot.sendMessage(chat_ID, text='GreenHouse added correctly!')
                    self.greenhouseCount = self.greenhouseCount + 1
                else:
                    self.bot.sendMessage(chat_ID, text='Error, try again.') 

            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for adding a greenhouse. To add a greenhouse send a message with the \
following format:\n/addGreenhouse\n<greenhouse_id>\n<plant_id>\n")
                

                
        elif command == "/getPlantList":
            if len(lines) == 1:
                self.bot.sendMessage(chat_ID, text="")
            
            elif len(lines) == 2:
                com = lines[1].split(":")[0].replace(" ","")
                if com == "id":
                    plantID = lines[1].split(":")[1].replace(" ","")
                    needs = requests.get("http://" + self.databaseIP + "?coll=plants&id="+plantID).json()



            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for searching a plant. To add a greenhouse send a message with the \
following format:")

            






        else:
            self.bot.sendMessage(chat_ID, text="The command you sent is not in our list. Check again the list of possible commands. \
\n/addUser\n/addGreenhouse\n/getPlantList")




















if __name__ == "__main__":
    #conf = json.load(open("settings.json"))
    conf = {"telegramToken": "6226505200:AAFJfAUnwZqRHwk8tH5YbNweoKKKYm0Tufk", "port":8080}
    token = conf["telegramToken"]
    token = 0
    cherryConf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }
    cherrypy.config.update(
        {'server.socket_host': '0.0.0.0', 'server.socket_port': conf["port"]})
    bot = RESTBot(token)
    cherrypy.tree.mount(bot, '/', cherryConf)
    cherrypy.engine.start()
    cherrypy.engine.block()