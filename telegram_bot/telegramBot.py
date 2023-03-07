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
        self.serv_cat_addr = str(conf_dict["services_catalog"]["ip"])+":"+ str(conf_dict["services_catalog"]["port"])
        self.myIP = str(conf_dict["telegram"]["endpoints_details"][0]["ip"]) +":"+ str(conf_dict["telegram"]["endpoints_details"][0]["port"])
        self.tokenBot=requests.get("http://" + self.serv_cat_addr + "/telegram").json()["telegram_token"]
        self.bot = telepot.Bot(self.tokenBot)
        self.currentGH = None
        self.databaseIP = requests.get("http://" + self.serv_cat_addr + "/service?name=mongoDB").json()["endpoints_details"]["address"]
        self.myDict = conf_dict["telegram"]
        
        self._registered_at_catalog = False
        self._last_update_serv = 0
        self.registerAtServiceCatalog()

        # Local variables for preventing failures
        self._users_local = []
        self._gh_local = []

        # In case of bot failure, the users need to be recovered from the services catalog
        # NOTE: these 2 methods are called at startup ONLY
        self.recoverUsers()
        self.recoverGreenhouses()

        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query':self.on_callback_query}).run_as_thread()
    


    ########################
    # SEND A LIST OF PLANT #                                                                                      
    ########################
    # Given a list of plant and a user, send to the user the list in the format <plant_name:plant_id>
    def sendPlantList(self, plantListDict, chat_ID):
        plantList = [json.loads(el) for el in list(plantListDict)]
        print(plantList)
        if len(plantList)==0:
            self.bot.sendMessage(chat_ID, text="No plant in our database match your requirements.")
        else:
            message = "Here is a list of plants that match your requirements:"
            for current in plantList:
                print(current)
                currentMessage = "\n"+current["name"]+" : "+ str(current["_id"])
                message = message+currentMessage
            self.bot.sendMessage(chat_ID, text=message)
    


    ##########################
    # SEND PLANT INFORMATION #                                                                                      
    ##########################
    def sendPlantInformation(self, information, chat_ID):

        message = "Information about the selected plant:\n"
        message = message + "ID: "+str(information["_id"])+"\nName: "+str(information["name"])+"\nCategory: "+str(information["category"])
        size = "\nSize range: "+str(information["size"][0])+"-"+str(information["size"][1])
        light = "\nLight range: "+str(information["min_light_lux"])+"-"+str(information["max_light_lux"])
        temperature = "\nTemperature range: "+str(information["min_temp"])+"-"+str(information["max_temp"])
        humidity = "\nHumidity range: "+str(information["min_env_humid"])+"-"+str(information["max_env_humid"])
        soil = "\nSoil moisture range: "+str(information["min_soil_moist"])+"-"+str(information["max_soil_moist"])
        generalInfo = "\n"+ str(information["soil"])+". "+str(information["sunlight"])+". "+str(information["watering"])+". "+str(information["fertilization"])+". "+str(information["pruning"])+".  "+str(information["blooming"])+". "+str(information["color"])+"."
        message = message + size + light + temperature + humidity + soil + generalInfo
        self.bot.sendPhoto(chat_id=chat_ID, photo=str(information["image"]))
        self.bot.sendMessage(chat_ID, text=message)



    ##################################
    # MANAGING THE RECEIVED MESSAGES #                                                                                      
    ##################################
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
                                "greenhouse": list(), 
                                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                self._users_local.append(myDictionary)
                
                buttons = [[InlineKeyboardButton(text=f'YES', callback_data=f'YESuser'),InlineKeyboardButton(text=f'NO', callback_data=f'NOuser')]]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(chat_ID, text="Are you sure you want to save this user", reply_markup=keyboard)

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
                    needs = requests.get(self.databaseIP + "?coll=plants&id="+plantID+"&needs=1").json()["needs"]
                    myDictionary = {"id": lines[1].replace(" ",""),  
                                    "user_id": chat_ID,
                                    "device_id": lines[1].replace(" ",""),
                                    "plant_type": lines[2].replace(" ",""),
                                    "plant_needs": needs}
                    
                    self.currentGH = myDictionary
                    
                    buttons = [[InlineKeyboardButton(text=f'YES', callback_data=f'YESgh'),InlineKeyboardButton(text=f'NO', callback_data=f'NOgh')]]
                    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                    self.bot.sendMessage(chat_ID, text="Are you sure you want to add this greenhouse", reply_markup=keyboard)

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
                        plantList = requests.get(self.databaseIP + "?coll=plants&category="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)

                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                elif parameter == "temperature":

                    try:
                        r = requests.get(self.databaseIP + "?coll=plants&temperature="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "humidity":
                    try:
                        plantList = requests.get(self.databaseIP + "?coll=plants&humidity="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "lux":
                    
                    try:
                        plantList = requests.get(self.databaseIP + "?coll=plants&lux="+value+"&N=10").json()
                        self.sendPlantList(plantList, chat_ID)
                    except:
                        self.bot.sendMessage(chat_ID, text="MongoDB is not answering.")

                
                elif parameter == "moisture":
                    
                    try:
                        plantList = requests.get(self.databaseIP + "?coll=plants&moisture="+value+"&N=10").json()
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
                        plantList = requests.get(self.databaseIP + "?coll=plants&min_size="+value1+"&max_size="+value2+"&N=5").json()
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
                print(self.databaseIP + "?coll=plants&id="+plantID)
                try:
                    info = requests.get(self.databaseIP + "?coll=plants&id="+plantID).json()
                    print(info)
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

                self.bot.sendMessage(chat_ID, text="📊 To require a graph, send a message \
with the following format:\n/getGraph\n<type_of_graph>\nThe type of graph can be temperature, precipitation, humidity or pressure")

            elif len(lines) == 2:

                requested = lines[1].replace(" ","")

                try:
                    if requested == "temperature":
                        image = requests.get(self.databaseIP+"?coll=weather&chart_temp=TRUE").json()["url"]
                        self.bot.sendMessage(chat_ID, text=image)

                    elif requested == "precipitation":
                        image = requests.get(self.databaseIP+"?coll=weather&chart_prec=TRUE").json()["url"]
                        self.bot.sendMessage(chat_ID, text=image)

                    elif requested == "humidity":
                        image = requests.get(self.databaseIP+"?coll=weather&chart_hum=TRUE").json()["url"]
                        self.bot.sendMessage(chat_ID, text=image)
                    
                    elif requested == "pressure":
                        image = requests.get(self.databaseIP+"?coll=weather&chart_press=TRUE").json()["url"]
                        self.bot.sendMessage(chat_ID, text=image)

                    else:
                        self.bot.sendMessage(chat_ID, text="The graph you required does not exist")

                except:
                    self.bot.sendMessage(chat_ID, text="MongoDB is not responding")


            else:

                self.bot.sendMessage(chat_ID, text="⚠️ Wrong format for requiring a graph. To require a graph, send a message \
with the following format:\n/getGraph\n<type_of_graph>\nThe type of graph can be either temperature or precipitation")


        ######################
        # GET MY INFORMATION #                                                                                      
        ######################
        elif command == "/myInformation":
            found = False
            info = None

            for i in self._users_local:
                if i["id"] == chat_ID:
                    info = i
                    found = True
            
            if found == True:
                message = "Your user profile has the following informations:\n"
                information = "- ID: "+str(info["id"])+"\n- User name: "+str(info["user_name"])+"\n- User surname: "+str(info["user_surname"])+"\n- Email address: "+str(info["email_addr"])+"\n- Greenhouse list:\n"
                message = message + information
                greenhouseList = info["greenhouse"]

                if len(greenhouseList) == 0:
                    currentMessage = "\nCurrently you have no greenhouse registered to the service."
                    message = message + currentMessage

                else:

                    try:
                        for gh in greenhouseList:
                            req = requests.get("http://"+self.serv_cat_addr+"/greenhouse?id="+str(gh))
                            current = req.json()
                            currentMessage = "    - Greenhouse: "+str(gh)+"\n        - Plant: "+current["plant_type"] + '\n'
                            message = message + currentMessage
                    except:
                        self.bot.sendMessage(chat_ID, text="Server is not responding")

                self.bot.sendMessage(chat_ID, text=message)

            else:
                self.bot.sendMessage(chat_ID, text="You have to create a user before getting your own informations.")



        ####################
        # IN CASE OF ERROR #                                                                                      
        ####################
        else:

            self.bot.sendMessage(chat_ID, text="The command you sent is not in our list. Check again the list of possible commands. \
\n/addUser\n/addGreenhouse\n/getPlantList")
            
    

    ########
    # POST #                                                                                      
    ########
    def POST(self, **param):
        listOfKeys = param.keys()
        if "greenhouseID" in listOfKeys and "required" in listOfKeys:
            greenhouseID = str(param["greenhouseID"])
            req = str(param["required"])
            try:
                resp = requests.get("http://"+self.serv_cat_addr+"/greenhouse?id="+greenhouseID).json()
                chat_ID = resp["user_id"]
                if req == "yes":
                    ########################################## ARRIVA FINO A QUA E POI SI ROMPE

                    self.bot.sendMessage(chat_ID, text="💧 The water in the tank of one of your greenhouse is low. You should refill it. The greenhouse ID is "+ greenhouseID)
                elif req == "no":
                    self.bot.sendMessage(chat_ID, text="🌧️ The water in the tank of one of your greenhouse is low. Tomorrow it is probably going to rain so it is not strictly equired to refill the tank. The greenhouse ID is "+ greenhouseID)
                else:
                    print("Wrong request (1)")
                    raise cherrypy.HTTPError(400, "Wrong request")

            except:
                print("Unable to contact the user as the services catalog is not responding")
                raise cherrypy.HTTPError(400, "Unable to contact the user as the services catalog is not responding")
        else:
            print("Wrong request (2)")
            raise cherrypy.HTTPError(400, "Wrong request") 

    ############
    # REGISTER #
    ############
    def registerAtServiceCatalog(self, max_tries=10):
        """
        This method is used to register the water delivery strategy
        information on the service catalog.
        -----
        Return values:
        - 1: registration successful
        - -1: information was already present - update was performed
        - 0: failed to add (unreachable server)
        """
        
        # Actual
        tries = 0
        addr = 'http://' + self.serv_cat_addr + '/service'
        print(addr)

        while not self._registered_at_catalog and tries < max_tries:
            tries += 1
            try:
                reg = requests.post(addr, json.dumps(self.myDict))
                print(self.myDict)
                
                if reg.ok:
                    self._registered_at_catalog = True
                    self._last_update_serv = time.time()
                    print("Successfully registered at service catalog!")
                    return 1
                elif reg.status_code == 400:
                    print("Device catalog was already registered!")
                    self._registered_at_catalog = True
                    # Perform an update, to keep the last_update recent
                    self.updateServCatalog()
                    return -1
                else:
                    print(f"Error {reg.status_code} - registration failed")
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                time.sleep(5)

        return 0


    ##########
    # UPDATE #                                                                                      
    ##########
    def updateServCatalog(self, max_tries=10):
        """
        Update the information at the services catalog.

        Return values:
        - 1: success
        - 0: fail
        - -1: had to register
        """
        updated = False
        tries = 0
        addr = 'http://' + self.serv_cat_addr + '/service'
        while not updated and tries < max_tries:
            tries += 1
            try:
                resp = requests.put(addr, data=json.dumps(self.myDict))
                if resp.ok:
                    print("Services catalog updated")
                    self._last_update_serv = time.time()
                    return 1
                else:
                    print(f"Error {resp.status_code} - unable to update services catalog")
                    if self.registerAtServiceCatalog() != 0:
                        print("Had to register!")
                        return 1
                    time.sleep(3)             
            except:
                print("Unable to reach services catalog for update")
                time.sleep(3)

        if tries == max_tries:
            self._registered_at_catalog = False
            if self.registerAtServiceCatalog() == 1:
                print("Had to register")
                return -1
        
        return 0
    
    def updateUsers(self, max_tries=10):
        addr = "http://" + self.serv_cat_addr + "/user"
        for current in self._users_local:    
            tries = 0
            curr_reg = False
            while tries < max_tries and not curr_reg:
                tries += 1
                try:
                    resp = requests.put(addr, data=json.dumps(current))
                    if resp.ok:
                        # User was registered correctly
                        print(f"Updated user {current['id']}")
                        curr_reg = True
                    else:
                        tries_2 = 0
                        curr_re_reg = False
                        while tries_2 < max_tries and not curr_re_reg:
                            tries_2 += 1
                            try:
                                r_up = requests.post(addr, data=json.dumps(current))
                                if r_up:
                                    curr_re_reg = True
                                    curr_reg = True
                                else:
                                    time.sleep(3)
                            except:
                                time.sleep(3)
                except:
                    time.sleep(3)

    def updateGreenhouses(self, max_tries=10):
        addr = "http://" + self.serv_cat_addr + "/greenhouse"
        for current in self._gh_local:    
            tries = 0
            curr_reg = False
            while tries < max_tries and not curr_reg:
                tries += 1
                try:
                    resp = requests.put(addr, data=json.dumps(current))
                    if resp.ok:
                        print(f"Updated greenhouse {current['id']}")
                        curr_reg = True
                    else:
                        tries_2 = 0
                        curr_re_reg = False
                        while tries_2 < max_tries and not curr_re_reg:
                            tries_2 += 1
                            try:
                                r_up = requests.post(addr, data=json.dumps(current))
                                if r_up:
                                    curr_re_reg = True
                                    curr_reg = True
                                else:
                                    time.sleep(3)
                            except:
                                time.sleep(3)
                except:
                    time.sleep(3)
            
    def updatePipeline(self):
        self.updateServCatalog()
        time.sleep(2)
        self.updateUsers()
        time.sleep(2)
        self.updateGreenhouses()
        

    def recoverUsers(self, max_tries=10):
        """
        In case of need to restart the bot, the users can be recovered with this method
        from the services catalog.
        """
        addr = "http://" + self.serv_cat_addr + "/users"

        tries = 0
        while tries < max_tries and self._users_local == []:
            tries += 1
            try:
                req = requests.get(addr)
                usrlist = req.json()
                if req.ok:
                    if len(usrlist) > 0:
                        print("Recovered users")
                        self._users_local = usrlist
                    else:
                        print("No users were recovered!")
                    return 1
                else:
                    print(f"Error {req.status_code} - could not get user list")
                    time.sleep(3)
            except:
                print("Unable to contact services catalog to get users!")
                time.sleep(3)
        
        return 0
    
    def recoverGreenhouses(self, max_tries=10):
        """
        In case of need to restart the bot, the greenhouses can be recovered with this method
        from the services catalog.
        """
        addr = "http://" + self.serv_cat_addr + "/greenhouses"

        tries = 0
        while tries < max_tries and self._gh_local == []:
            tries += 1
            try:
                req = requests.get(addr)
                ghlist = req.json()
                if req.ok:
                    if len(ghlist) > 0:
                        print("Recovered users")
                        self._gh_local = ghlist
                    else:
                        print("No greenhouses were recovered!")
                    return 1
                else:
                    print(f"Error {req.status_code} - could not get greenhouse list")
                    time.sleep(3)
            except:
                print("Unable to contact services catalog to get greenhouses!")
                time.sleep(3)
        
        return 0


    #####################
    # CALLBACK FUNCTION #                                                                                      
    #####################
    def on_callback_query(self,msg):

        query_ID, chat_ID, query_data = telepot.glance(msg, flavor='callback_query')
        if query_data == "YESuser":
            try:

                current = None
                for i in self._users_local:
                    if i["id"] == chat_ID:
                        current = i

                resp = requests.post("http://"+self.serv_cat_addr+"/user", json.dumps(i))
                print(i)

                if resp.status_code == 201:

                    self.bot.sendMessage(chat_ID, text='User added correctly!')
                    #self._users_local[chat_ID] = current

                elif resp.status_code == 400:

                    resp2 = requests.put("http://"+self.serv_cat_addr+"/user", json.dumps(i))
                    
                    if resp2.ok:
                        self.bot.sendMessage(chat_ID, text='User was updated') 
                    else:
                        self.bot.sendMessage(chat_ID, text='Error, try again.')
                        # Need to remove the added user
                        del self._users_local[-1]


            except:

                self.bot.sendMessage(chat_ID, text='The server is not responding, please try again later.')
        
        if query_data == "NOuser":

            current = None  
            for i in self._users_local:
                if i["id"] == chat_ID:
                    current = i

            self._users_local.remove(current)
            self.bot.sendMessage(chat_ID, text='User has not been added.')

        if query_data == "YESgh":
            try:

                print(self.currentGH)
                resp = requests.post("http://" + self.serv_cat_addr + "/greenhouse", json.dumps(self.currentGH)) 

                if resp.status_code == 201:
                    # Remove greenhouses with same ID from the local list
                    for gh in self._gh_local:
                        if gh["id"] == self.currentGH["id"]:
                            self._gh_local.remove(gh)
                    self._gh_local.append(self.currentGH)
                    self.bot.sendMessage(chat_ID, text='GreenHouse added correctly!')
                    print("http://" + self.serv_cat_addr + "/user?id="+str(chat_ID))
                    resp = requests.get("http://" + self.serv_cat_addr + "/user?id="+str(chat_ID))
                    for i in self._users_local:
                        if i["id"] == chat_ID:
                            i["greenhouse"] = resp.json()["greenhouse"]


                elif resp.status_code == 400:
                    # Allow user to overwrite greenhouses
                    for gh in self._gh_local:
                        if gh["id"] == self.currentGH["id"]:
                            self._gh_local.remove(gh)
                    count = 0
                    while count < 5:
                        count = 5
                        resp = requests.put("http://" + self.serv_cat_addr + "/greenhouse", json.dumps(self.currentGH))
                        if resp.ok:
                            self._gh_local.append(self.currentGH)
                            self.bot.sendMessage(chat_ID, text='New greenhouse replaced existing one with same ID.')

                    
            except:
                self.bot.sendMessage(chat_ID, text='The server is not responding, please try again later.')

        if query_data == "NOgh":

            self.currentGH = None
            self.bot.sendMessage(chat_ID, text='The greenhouse has not been added.')
        


########
# MAIN #                                                                                      
########
if __name__ == "__main__":
    conf_dict = json.load(open("settings.json"))
    cherryConf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': conf_dict["telegram"]["endpoints_details"][0]["port"]})
    bot = RESTBot(conf_dict)
    cherrypy.tree.mount(bot, '/', cherryConf)
    cherrypy.engine.start()
    
    try:
        while True:
            bot.updatePipeline()
            time.sleep(20)
    except KeyboardInterrupt:
        cherrypy.engine.stop()
