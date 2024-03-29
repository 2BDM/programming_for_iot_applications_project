import cherrypy
import mongoDB_adaptor as mDB
import json as js
import requests
import time

class adaptor_mongo_interface(object):
    exposed = True
    
    
    #############################################################################################
    # In this method each case is identified by different parameters:                           #
    # - coll            --> to select the right collection                                      #
    #   - coll = "plants"                                                                       #
    #           - id, needs=1             --> to have the list of needs of a plant (given ID)   #
    #           - id                      --> to search by id (retrieves all information)       #
    #           - name                    --> to search by name (retrieves all information)     #
    #           - min_size, max_size, N   --> to search by size                                 #
    #           - category, N             --> to search by category                             #
    #           - temperature, N          --> to search by temperature                          #
    #           - humidity, N             --> to search by value of humidity                    #
    #           - lux, N                  --> to search by the value of light                   #
    #           - moisture, N             --> to search by moisture                             #
    #   - coll = "weather"                                                                      #
    #           - date                    --> to search by a specific date                      #
    #           - min_date, max_date      --> to search records in a interval of dates          #
    #           - chart_temp              --> to have the chart of min, max and mean temperature#
    #           - chart_prec              --> to have the chart of precipitations               #
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
        self.port = self.conf_dict["mongo_db"]["endpoints_details"][0]["port"]
        self.ip = "0.0.0.0" # self.conf_dict["mongo_db"]["endpoints_details"][0]["ip"]
        self.addr = "http://" + str(self.ip) + ":" + str(self.port)
        
        #information of database
        url = self.conf_dict["database"]["url_database"]
        database_name = self.conf_dict["database"]["database_name"]
        self.coll1_name = self.conf_dict["database"]["collections"][0]
        self.coll2_name = self.conf_dict["database"]["collections"][1]
        self.mongoP = mDB.mongoAdaptor(url,database_name,self.coll1_name)
        self.mongoW = mDB.mongoAdaptor(url,database_name,self.coll2_name)
        
        #information of charts
        self.url_chart_temp = self.conf_dict["charts"]["url_temp"]
        self.url_chart_prec = self.conf_dict["charts"]["url_precipitations"]
        self.url_chart_pressure = self.conf_dict["charts"]["url_pressure"]
        self.url_chart_hum = self.conf_dict["charts"]["url_hum"]

        tmpDict = self.conf_dict["mongo_db"]
        tmpdetails = tmpDict["endpoints_details"][0]
        tmpdetails.pop('ip')
        tmpdetails.pop('port')
        tmpDict["endpoints_details"]=tmpdetails
    
    def getPort(self):
        return self.port
    
    def getIP(self):
        return self.ip
    
    def GET(self, *uri, **params):
        value = params.keys()
        print(self.coll1_name)
        if 'coll' in params.keys():
            if params['coll']==self.coll1_name:
                

                if "id" in value and "needs" in value:
                    return self.mongoP.find_by_id_needs(int(params['id']))
                    
                elif "id" in value:
                    return self.mongoP.find_by_id(int(params['id']))
                    
                elif "min_size" in value and "max_size" in value and "N" in value:
                    return self.mongoP.find_by_size(int(params['min_size']),int(params['max_size']),int(params['N']))
            
                elif "name" in value:
                    return self.mongoP.find_by_name(params['name'])
                
                elif "category" in value and "N" in value:
                    out = self.mongoP.find_by_category(str(params['category']),int(params['N']))
                    print(out)
                    return js.dumps(out)

                elif "temperature" in value and "N" in value:
                    return js.dumps(self.mongoP.find_by_temperature(int(params['temperature']),int(params['N'])))
                
                elif "humidity" in value and "N" in value:
                    return js.dumps(self.mongoP.find_by_humidity(int(params['humidity']),int(params['N'])))
                
                elif "lux" in value and "N" in value:
                    return js.dumps(self.mongoP.find_by_lux(int(params['lux']),int(params['N'])))
                
                elif "moisture" in value and "N" in value:
                    return js.dumps(self.mongoP.find_by_moisture(int(params['moisture']),int(params['N'])))

                    
            elif params['coll']==self.coll2_name:
                if "date" in value:
                    return self.mongoW.find_by_timestamp(str(params['date']))
                elif "min_date" in value and "max_date" in value:
                    return self.mongoW.find_by_timestamp(str(params['min_date']),str(params['max_date']))
                elif "chart_temp" in value:
                    return js.dumps({"url":self.url_chart_temp})
                elif "chart_prec" in value:
                    return js.dumps({"url":self.url_chart_prec})
                elif "chart_press" in value:
                    return js.dumps({"url":self.url_chart_press})
                elif "chart_hum" in value:
                    return js.dumps({"url":self.url_chart_hum})
            else:
                return "Check the introduced parameters - no match found"   
        
    
    def POST(self,**params):
        bodyAsString = cherrypy.request.body.read()
        newDataDict = js.loads(bodyAsString)
        if params['coll'] == "weather":
            self.mongoW.insert_one_dict(newDataDict)
            
    
    def registerAtServCat(self,max_tries=1):
        # TODO --> ask for new ID
        if not self.own_ID:
            try:
                id = requests.get(self.addr_ser_cat + "/new_serv_id")
                self.conf_dict["id"]=id
            except:
                print("Connection not establish - no id retrieved")
                    
        # I'm preparing the dictionary to send to the service catalog
        tmpDict = self.conf_dict["mongo_db"]
 
        tries = 0
        if self.addr_ser_cat != "":
            addr = self.addr_ser_cat + "/service"
            while tries <= max_tries and not self._registered_dev_cat:  
                try:
                    r = requests.post(addr, data=js.dumps(tmpDict))
                    if r.ok:
                        self._registered_dev_cat = True
                        print("Registered!")
                    elif r.status_code == 400:
                        print("Device was already registered!\n↓")
                        self._registered_dev_cat = True
                        if self.updateServCat() == 1:
                            return 1
                        else:
                            print("Unable to update info")
                    else:
                        print(f"Error {r.status_code} - unable to register info on services catalog")
                    tries += 1
                    time.sleep(3)
                except:
                    print("Tried to register at services catalog - failed to establish a connection!")
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

    def updateServCat(self, max_tries=10):
        """
        This ethod is used to update the information of the device catalog 
        at the services catalog.
        ------
        Return values:
        - 1: update successful
        - -1: needed to register first
        - 0: unable to reach server
        """
        # Try refreshing info (PUT) - code 200
        # If it fails with code 400 -> cannot update
            # Perform POST

        updated = False
        count_fail = 0

        tmpDict = self.conf_dict["mongo_db"]

        while not updated and count_fail < max_tries:
            count_fail += 1
            try:
                try1 = requests.put(self.addr_ser_cat + '/service', data=js.dumps(tmpDict))

                # If here, it was possible to send the request to the server (reachable)
                if try1.status_code == 200:
                    # Update successful
                    print("Information in the service catalog was successfully updated!")
                    self._last_update_serv = time.time()
                    return 1
                elif try1.status_code == 400:
                    print("Unable to update information at the service catalog ---> trying to register")
                    self._registered_dev_cat = False
                    self.registerAtServCat()
                    if self._registered_dev_cat:
                        updated = True
                        return -1
                else:
                    print(f"Error {try1.status_code} - could not update service info")
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                time.sleep(5)
        
        # If here, then it was not possible to update nor register information
        # within the maximum number of iterations, which means it was not possible 
        # to reach the server
        print("Maximum number of tries exceeded - service catalog was unreachable!")
        return 0


if __name__ == "__main__":
    # Standard configuration to serve the url "localhost:8080"
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    webService = adaptor_mongo_interface("mongo_conf.json", True)
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_host': webService.getIP()})
    cherrypy.config.update({'server.socket_port': webService.getPort()})

    ok = False
    max_iter_init = 10
    iter_init = 0

    while not ok:
        init_status = webService.registerAtServCat(max_tries=10)
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

    try:
        while True:
            time.sleep(5)
            webService.updateServCat()
    except KeyboardInterrupt:
        cherrypy.engine.stop()
