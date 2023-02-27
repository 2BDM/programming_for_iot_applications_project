import cherrypy
import mongoDB_adaptor as mDB
import json as js

class adaptor_mongo_interface(object):
    exposed = True
    
    
    #############################################################################################
    # In this method each case is identified by different parameters:                           #
    # - coll            --> to select the right collection                                      #
    #   - coll = "plants"                                                                       #
    #           - id                      --> to search by id                                   #
    #           - min_size, max_size, N   --> to search by size                                 #
    #           - category, N             --> to search by category                             #
    #           - temperature, N          --> to search by temperature                          #
    #           - humidity, N             --> to search by value of humidity                    #
    #           - lux, N                  --> to search by the value of light                   #
    #           - moisture, N             --> to search by moisture                             #
    #   - coll = "weather"                                                                      #
    #           - date                    --> to search by a specific date                      #
    #           - min_date, max_date      --> to search records in a interval of dates          #
    # VERY IMPORTANT:                                                                           #
    # All the requests (except for the ID) return N records of type [{"_id":id},{"name":name}]  #
    # and not the full information. So, you should make two requests.                           #
    #############################################################################################
    
    def __init__(self,conf_file,own_ID = False):
        self._registered_dev_cat = False
        self.own_ID = own_ID
        self.conf_dict = js.load(open(conf_file))
        # information of service catalog
        self.addr_ser_cat = "http://" + self.conf_dict["services_catalog"]["ip"] + ":" + str(self.conf_dict["services_catalog"]["port"])
        
        # information of mongoDB
        self.port = self.conf_dict["mongo_db"]["endpoints_details"]["port"]
        self.ip = self.conf_dict["mongo_db"]["endpoints_details"]["ip"]
        self.addr = "http://" + str(self.ip) + ":" + str(self.port)
        
        #information of database
        url = self.conf_dict["url_database"]
        database_name = self.conf_dict["database_name"]
        coll1_name = self.conf_dict["mongo_db"]["collections"][0]
        coll2_name = self.conf_dict["mongo_db"]["collections"][1]
        self.mongoP = mDB.mongoAdaptor(url,database_name,coll1_name)
        self.mongoW = mDB.mongoAdaptor(url,database_name,coll2_name)
    
    def getPort(self):
        return self.port
    
    def getIP(self):
        return self.ip
    
    def GET(self, *uri, **params):
        value = params.keys()
        if params['coll']==coll1_name:
            if "id" in value:
                return self.mongoP.find_by_id(int(params['id']))
            
            elif "min_size" in value and "max_size" in value and "N" in value:
                return self.mongoP.find_by_size(int(params['min_size']),int(params['max_size']),int(params['N']))
            
            elif "category" in value and "N" in value:
                return self.mongoP.find_by_category(str(params['category']),int(params['N']))
            
            elif "temperature" in value and "N" in value:
                return self.mongoP.find_by_temperature(int(params['temperature']),int(params['N']))
            
            elif "humidity" in value and "N" in value:
                return self.mongoP.find_by_humidity(int(params['humidity']),int(params['N']))
            
            elif "lux" in value and "N" in value:
                return self.mongoP.find_by_lux(int(params['lux']),int(params['N']))
            
            elif "moisture" in value and "N" in value:
                return self.mongoP.find_by_moisture(int(params['moisture']),int(params['N']))
        elif params['coll']==coll2_name:
            if "date" in value:
                return self.mongoW.find_by_timestamp(str(params['date']))
            elif "min_date" in value and "max_date" in value:
                return self.mongoW.find_by_timestamp(str(params['min_date']),str(params['max_date']))
        else:
            return "error"   
    
    def POST(self,**params):
        bodyAsString = cherrypy.request.body.read()
        newDataDict = js.loads(bodyAsString)
        if params['coll'] == "weather":
            self.mongoW.insert_one_dict(newDataDict)
            
    
    def registerAtServCat(self,tries):
        tries = 0
        # TODO --> ask for new ID
        if not self.own_ID:
            pass
        # I'm preparing the dictionary to send to the service catalog
        tmpDict = self.conf_dict["mongo_db"]
        tmpDict.pop("ip",None)
        tmpDict.pop("port",None)
        
        if self.addr_ser_cat != {}:
            addr = addr_dev_cat + "/service"
            while tries <= max_tries and not self._registered_dev_cat:  
                try:
                    r = requests.post(addr, data=json.dumps(tmpDict))
                    if r.ok:
                        # self.dev_cat_info = r.json()
                        self._registered_dev_cat = True
                        print("Registered!")
                    elif r.status_code == 400:
                        print("Device was already registered!\n↓")
                        self._registered_dev_cat = True
                        if self.updateDevCat() == 1:
                            return 1
                        else:
                            print("Unable to update info")
                    else:
                        print(f"Error {r.status_code} - unable to update device information on device catalog")
                    tries += 1
                    time.sleep(3)
                except:
                    print("Tried to register at device catalog - failed to establish a connection!")
                    tries += 1
                    time.sleep(3)
            
            if self._registered_dev_cat:
                # Success
                return 1
            else:
                # Not registered
                return 0
        else: 
            print("Missing information on service catalog!")
            return -1


if __name__ == "__main__":
    # Standard configuration to serve the url "localhost:8080"
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }
    webService = adaptor_mongo_interface("mongo_conf.json", True)
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_host': webService.getIP()})
    cherrypy.config.update({'server.socket_port': webService.getPort()})
    
     ############### Start operation ###############

    ok = False
    max_iter_init = 10
    iter_init = 0

    while not ok:
        init_status = webService.registerAtServCat(max_tries=100)

        if init_status == 1:
            # Correctly registered
            ok = True
        elif init_status == 0:
            iter_init += 1

        if iter_init >= max_iter_init:
            # If too many tries - wait some time, then retry
            iter_init = 0
            time.sleep(10)
        
    cherrypy.engine.start()
    cherrypy.engine.block()