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
    def __init__(self,conf_file):
        f = open(conf_file,'r')
        self.conf_dict = js.load(f)
        # information of service catalog
        self.addr_ser_cat = "http://" + self.conf_dict["services_catalog"]["ip"] + ":" + str(self.conf_dict["services_catalog"]["port"])
        
        # information of mongoDB
        self.port = self.dict["mongoDB"]["endpoints_details"]["port"]
        self.ip = self.dict["mongoDB"]["endpoints_details"]["ip"]
        self.addr = "http://" + str(self.ip) + ":" + str(self.port)
        url = "mongodb+srv://2BDM:Gruppo17@2bdm.bxvbkre.mongodb.net/"
        self.mongoP = mDB.mongoAdaptor(url,"IOT_project","plants")
        self.mongoW = mDB.mongoAdaptor(url,"IOT_project","weather")
    
    
    def GET(self, *uri, **params):
        value = params.keys()
        if params['coll']=="plants":
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
        elif params['coll']=="weather":
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
        


if __name__ == "__main__":
    # Standard configuration to serve the url "localhost:8080"
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }
    webService = adaptor_mongo_interface()
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_port': webService.})
    cherrypy.engine.start()
    cherrypy.engine.block()