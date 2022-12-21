import time
from datetime import datetime
import cherrypy
import json

"""
This program contains the service catalog for the application
"""


class Catalog():
    """ 
    Catalog class
    ---
    Used to handle an application catalog keeping track of the
    connected devices and available resources
    """
    def __init__(self, in_path, out_path):
        self.cat = json.load(open(in_path))
        self.out_path = out_path
        self.lastupdate = time.time()
        self.dev_params = ["id", "name", "endpoints", 
                    "endpoints_details", "greenhouse", 
                    "resources"]
        self.usr_params = ["id", "user_name", "user_surname", 
                    "email_addr", "greenhouse"]
        self.sens_params = ["id", "deviceName", "measureType", 
                        "device_id", "availableServices", "servicesDetails"]

    def saveAsJson(self):
        # Used to save a local copy of the current dictionary
        try:
            json.dump(self.cat, open(self.out_path, "w"))
            return 1
        except:
            return 0

    def searchDevice(self, parameter, value):
        elem = {}
        for elem_cat in self.cat["devices"]:
            if elem_cat[parameter] == value:
                # Supposing no duplicates
                elem = elem_cat.copy()
        
        return elem

    def searchUser(self, parameter, value):
        elem = {}
        for elem_cat in self.cat["users"]:
            if elem_cat[parameter] == value:
                # Supposing no duplicates
                elem = elem_cat.copy()
        
        return elem

    def searchSens(self, device_id, parameter, value):
        """
        Search for sensor given the device ID and the parameter 
        over which to perform the search
        """
        
        elem = {}
        for elem_cat in self.cat["devices"]:
            if elem_cat["id"] == device_id:
                for sens in elem_cat["resources"]["sensors"]:
                    if sens[parameter] == value:
                        elem = sens.copy()
        
        return elem

    def addDevice(self, newDev):
        # Check body contains the right fields
        # has_key() method
        
        if all(elem in newDev for elem in self.dev_params):
            # can proceed to adding the element
            new_id = newDev["id"]
            if self.searchDevice("id", new_id) == {}:
                # not found
                newDev["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["devices"].append(newDev)
                return new_id

        return 0    # Element is either invalid or already exists

    def addUser(self, newUsr):
        # Check body contains the right fields
        # has_key() method
        
        if all(elem in newUsr for elem in self.usr_params):
            # can proceed to adding the element
            new_id = newUsr["id"]
            if self.searchUser("id", new_id) == {}:
                # not found
                newUsr["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["users"].append(newUsr)
                return new_id

        return 0    # Element is either invalid or already exists

    def addSensor(self, newSens):
        # Check body contains the right fields
        # has_key() method
        
        if all(elem in newSens for elem in self.sens_params):
            # can proceed to adding the element
            dev_id = newSens["device_id"]
            sens_id = newSens["id"]
            for ind in range(len(self.cat["devices"])):
                # Find correct device
                if self.cat["devices"][ind]["id"] == dev_id:
                    sens_found = False
                    for sens in self.cat["devices"][ind]["resources"]["sensors"]:
                        if sens["id"] == sens_id and not sens_found:
                            sens_found = True
                    
                    if not sens_found:
                        newSens["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.cat["devices"][ind]["resources"]["sensors"].append(newSens)
                        return sens_id

        return 0    # Element is either invalid or already exists

    def updateDevice(self, updDev):
        # Check fields
        if all(elem in updDev for elem in self.dev_params):
            # Find device
            for ind in range(len(self.cat["devices"])):
                if self.cat["devices"][ind]["id"] == updDev["id"]:
                    for key in self.dev_params:
                        self.cat["devices"][ind][key] = updDev[key]
                    self.cat["devices"][ind]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return updDev["id"]
        
        return 0
    
    def updateUser(self, updUsr):
        # Check fields
        if all(elem in updUsr for elem in self.usr_params):
            # Find device
            for ind in range(len(self.cat["users"])):
                if self.cat["users"][ind]["id"] == updUsr["id"]:
                    for key in self.usr_params:
                        self.cat["users"][ind][key] = updUsr[key]
                    self.cat["users"][ind]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return updUsr["id"]
            
        return 0

    def updateSensor(self, updSens):
        # Check fields
        if all(elem in updSens for elem in self.sens_params):
            # Find device
            for ind in range(len(self.cat["devices"])):
                if self.cat["devices"][ind]["id"] == updSens["device_id"]:
                    for ind2 in range(len(self.cat["devices"][ind]["resources"]["sensors"])):
                        if self.cat["devices"][ind]["resources"]["sensors"][ind2]["id"] == updSens["id"]:
                            # Update device (found)
                            for key in self.sens_params:
                                self.cat["devices"][ind]["resources"]["sensors"][ind2][key] = updSens[key]
                            self.cat["devices"][ind]["resources"]["sensors"][ind2]['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            return updSens["id"]
                
        return 0

    def cleanDevices(self, curr_time, timeout):
        """
        Clean up old device records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        n_rem = 0
        for ind in range(len(self.cat["devices"])):
            dev_time = datetime.timestamp(datetime.strptime(self.cat["devices"][ind]["last_update"], "%Y-%m-%d %H:%M:%S"))
            if curr_time - dev_time > timeout:
                # Delete record
                self.cat["devices"].remove(self.cat["devices"][ind])
                n_rem += 1
        
        return n_rem

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


    

class CatalogWebService():
    """
    CatalogWebService
    ---
    Used to 
    """

    exposed = True

    def __init__(self, catalog_path, cmd_list_cat, output_cat_path="catalog_updated.json"):
        #self.catalog = json.load(open(catalog_path))
        self.commandList = json.load(open(cmd_list_cat))
        self.catalog = Catalog(catalog_path, output_cat_path)
        self.msg_ok = {"status": "SUCCESS", "msg": ""}
        self.msg_ko = {"status": "FAILURE", "msg": ""}
        self.timeout = 120          # seconds

    def GET(self, *uri, **params):
        # Depending on uri path, show what is required
        if (len(uri) >= 1):
            if (str(uri[0]) == "broker"):
                # Return broker info
                return json.dumps(self.catalog.cat["broker"])
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

    WebService = CatalogWebService("serv_catalog.json", "cmdList.json")

    #threading.Timer(60, WebService.cleanRecords()).start()

    cherrypy.tree.mount(WebService, '/', conf)
    # cherrypy.config.update({'server.socket_host': '192.168.64.152'})
    cherrypy.engine.start()
    while True:
        time.sleep(60)
        WebService.cleanRecords()
    cherrypy.engine.block()
