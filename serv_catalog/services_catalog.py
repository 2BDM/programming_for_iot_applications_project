import time
from datetime import datetime
import cherrypy
import json

"""
This program contains the services catalog for the application
"""


class ServicesCatalog():
    """ 
    ServicesCatalog class
    """

    def __init__(self, in_path, out_path):
        self.cat = json.load(open(in_path))
        self.out_path = out_path
        self.lastupdate = time.time()

        # For checking at insertion:
        self._dev_cat_params = ["ip", "ports", "methods"]
        self._usr_params = ["id", "user_name", "user_surname", 
                    "email_addr", "greenhouse"]
        self._sens_params = ["id", "deviceName", "measureType", 
                        "device_id", "availableServices", "servicesDetails"]

        self._default_dev_cat = {
            "ip": "", "port": -1, "methods": []
            }

    def saveAsJson(self):
        # Used to save a local copy of the current dictionary - returns 1 if success, else 0
        try:
            json.dump(self.cat, open(self.out_path, "w"))
            return 1
        except:
            return 0

    # GETTERS: they all return a python dictionary
    
    def gerProjectName(self):
        return self.cat["project_name"]
    
    def gerProjectOwner(self):
        return self.cat["project_owner"]

    def getBroker(self):
        return self.cat["broker"]

    def getTelegram(self):
        return self.cat["telegram"]

    def getDevCatalog(self):
        # Not hard-coded: need to check it is not empty!
        if self.cat["device_catalog"]["last_update"] != "":
            return self.cat["device_catalog"]
        else:
            return {}

    # SEARCHES: search for specific record

    def searchUser(self, parameter, value):
        elem = {}
        for elem_cat in self.cat["users"]:
            if elem_cat[parameter] == value:
                # Supposing no duplicates
                elem = elem_cat.copy()
        
        return elem

    # ADDERS: add new records

    def addDevCat(self, device_catalog):
        if all(elem in device_catalog for elem in self._dev_cat_params):
            pass

    def addUser(self, newUsr):
        # Check body contains the right fields
        # has_key() method
        
        if all(elem in newUsr for elem in self._usr_params):
            # can proceed to adding the element
            new_id = newUsr["id"]
            if self.searchUser("id", new_id) == {}:
                # not found
                newUsr["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["users"].append(newUsr)
                return new_id

        return 0    # Element is either invalid or already exists

    # UPDATERS: update records
    
    def updateUser(self, updUsr):
        # Check fields
        if all(elem in updUsr for elem in self._usr_params):
            # Find device
            for ind in range(len(self.cat["users"])):
                if self.cat["users"][ind]["id"] == updUsr["id"]:
                    for key in self._usr_params:
                        self.cat["users"][ind][key] = updUsr[key]
                    self.cat["users"][ind]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return updUsr["id"]
            
        return 0

    # CLEANERS: perform timeout check on records

    def cleanDevCat(self, curr_time, timeout):
        """
        Clean up device catalog records

        """
        oldtime = datetime.timestamp(datetime.strptime(self.cat["device_catalog"]["last_update"], "%Y-%m-%d %H:%M:%S"))
        if curr_time - oldtime > timeout:
            self.cat["device_catalog"] = self._default_dev_cat
            self.cat["device_catalog"]["last_update"] = ""

    def cleanUsers(self, curr_time, timeout):
        """
        Clean up old user records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        n_rem = 0
        for ind in range(len(self.cat["users"])):
            dev_time = datetime.timestamp(datetime.strptime(self.cat["users"][ind]["last_update"], "%Y-%m-%d %H:%M:%S"))
            if curr_time - dev_time > timeout:
                # Delete record
                self.cat["users"].remove(self.cat["users"][ind])
                n_rem += 1
        
        return n_rem


    

class ServicesCatalogWebService():
    """
    CatalogWebService
    ---
    Used to 
    """

    exposed = True

    def __init__(self, catalog_path, cmd_list_cat, output_cat_path="catalog_updated.json"):
        #self.catalog = json.load(open(catalog_path))
        self.commandList = json.load(open(cmd_list_cat))
        self.catalog = ServicesCatalog(catalog_path, output_cat_path)
        self.msg_ok = {"status": "SUCCESS", "msg": ""}
        self.msg_ko = {"status": "FAILURE", "msg": ""}
        self.timeout = 120          # seconds

    def GET(self, *uri, **params):
        # Depending on uri path, show what is required
        if (len(uri) >= 1):
            if (str(uri[0]) == "broker"):
                # Return broker info
                return json.dumps()
            elif (str(uri[0]) == "devices"):
                # Return all devices info
                return json.dumps(self.catalog.cat["devices"])
            elif (str(uri[0]) == "device"):
                # Return info of specific device whose ID is a parameter
                dev_ID = int(params["ID"])
                # Find device
                dev_found = self.catalog.searchDevice("id", dev_ID)
                if dev_found != {}:
                    return json.dumps(dev_found)
                else:
                    raise cherrypy.HTTPError(404, "Device not found")
            elif (str(uri[0]) == "users"):
                # Return info of all users
                return json.dumps(self.catalog.cat["devices"])
            elif (str(uri[0]) == "user"):
                # Return info of specified user
                usr_ID = int(params["ID"])
                usr_found = self.catalog.searchUser("id", usr_ID)
                if usr_found != {}:
                    return json.dumps(usr_found)
                else:
                    raise cherrypy.HTTPError(404, "User not found")
        else:       # Default case
            return json.dumps(self.commandList["methods"][0])

    def POST(self, *uri, **params):
        """ 
        Used to add new records (users/devices)
        """
        body = json.loads(cherrypy.request.body.read()) # Dictionary

        if (len(uri) >= 1):
            if (str(uri[0]) == "device"):
                if self.catalog.addDevice(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Device " + str(body["id"]) + " was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add device"
                    cherrypy.response.status = 400
                    return json.dumps(out)

            elif (str(uri[0]) == "user"):
                if self.catalog.addUser(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "User " + str(body["id"]) + " was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add user"
                    cherrypy.response.status = 400
                    return json.dumps(out)

            elif (str(uri[0]) == "sensor"):
                if self.catalog.addSensor(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Sensor " + str(body["id"]) + " was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add sensor"
                    cherrypy.response.status = 400
                    return json.dumps(out)
        
        else:
            return "Insert devices in /device and users in /user"
                

    def PUT(self, *uri, **params):
        """
        Used to update existing records
        Use it at refresh (when services/devices keep updated the register)
        """
        body = json.loads(cherrypy.request.body.read())

        if (len(uri) >= 1):
            if (str(uri[0]) == "device"):
                if self.catalog.updateDevice(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Device " + str(body["id"]) + " was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update device"
                    cherrypy.response.status = 400
                    return json.dumps(out)

            elif (str(uri[0]) == "user"):
                if self.catalog.updateUser(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "User " + str(body["id"]) + " was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update user"
                    cherrypy.response.status = 400
                    return json.dumps(out)
        
        elif (str(uri[0]) == "sensor"):
                if self.catalog.updateSensor(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Sensor " + str(body["id"]) + " was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update sensor"
                    cherrypy.response.status = 400
                    return json.dumps(out)

        return "Update device info in /device, user info in /user and sensor info in /sensor"

    def cleanRecords(self):
        ## Check for old records (> 2 min)
        curr_time = time.time()

        rem_d = self.catalog.cleanDevices(curr_time, self.timeout)
        rem_u = self.catalog.cleanUsers(curr_time, self.timeout)
        
        if rem_d > 0 or rem_u > 0:
            self.catalog.saveAsJson()

        print(f"Removed {rem_d} devices, {rem_u} users")



def cleanupLoop(ws):
    while True:
        time.sleep(5)
        ws.cleanRecords()



if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True
        }
    }

    WebService = ServicesCatalogWebService("serv_catalog.json", "cmdList.json")

    cherrypy.tree.mount(WebService, '/', conf)
    # cherrypy.config.update({'server.socket_host': '192.168.64.152'})
    cherrypy.engine.start()
    while True:
        time.sleep(60)
        WebService.cleanRecords()
    cherrypy.engine.block()
