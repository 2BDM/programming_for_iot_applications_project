# Bot for the exam

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

        #for i in self.users:
        #    if i["id"] == chat_ID:
        #        self.users[""]

        message = msg["text"]
        lines = message.split("\t")

        if lines[0] == "/addUser":
            if len(lines) == 4:
                myDictionary = {"id": chat_ID, 
                                "user_name": lines[1], 
                                "user_surname": lines[2], 
                                "email_addr": lines[3], 
                                "telegram_id": chat_ID, 
                                "greenhouse": list(), 
                                "last_update": time.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                resp = requests.post("http://" + self.catalogIP + "/user", json = myDictionary)  
                if resp.status_code == 200:
                    self.bot.sendMessage(chat_ID, text='User added correctly!')
                    #self.users.append(chat_ID : myDictionary)
                else:
                    self.bot.sendMessage(chat_ID, text='Error, try again.') 

            else:
                self.bot.sendMessage(chat_ID, text="Wrong format for adding a user.\
                                     To add a user send a message with the following format:\n\
                                    /addUser\n\
                                    <user_name>\n\
                                    <user_surname>\n\
                                    <email_address>")
        
        elif lines[0] == "/addGreenhouse":
            if len(lines) == 3:
                plantID = lines[2]
                needs = requests.get("http://" + self.databaseIP + "?coll=plants&id="+plantID).json()["IP"]
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
                self.bot.sendMessage(chat_ID, text="Wrong format for adding a greenhouse.\
                                     To add a user send a message with the following format:\n\
                                    /addGreenhouse\n\
                                    <name>\n\
                                    <plant_id>")
                
        elif lines[0] == "/getPlantList":
            completeList = requests.get("http://" + self.databaseIP + "?coll=plants").json()



















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