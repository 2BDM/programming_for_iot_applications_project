import time
from datetime import datetime
import cherrypy
import json
import sys

"""
This program contains the services catalog for the application
------------------------------------------------------------------
Web service info:
- Running on localhost
- Port 8080
"""


class ServicesCatalog():
    """ 
    ServicesCatalog class
    """

    def __init__(self, in_path, out_path="serv_cat_updated.json"):
        # Allow to use fac-simile catalog for testing
        try:
            self.cat = json.load(open(in_path))
        except:
            print("Default catalog taken")
            self.cat = json.load(open("serv_catalog.json"))
        
        self._serv_cat_params = ['project_name', 'project_owner',
                        'services_catalog', 'broker', 'telegram', 
                        'device_catalog', 'users', 'greenhouses',
                        "services"]

        # Check for valid catalog
        if all(elem for elem in self.cat for elem in self._serv_cat_params):
            print("Valid catalog!")
        else:
            raise KeyError("Wrong catalog syntax!")
        
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cat["last_update"] = self.last_update

        # For checking at insertion:
        self._dev_cat_params = ["ip", "port", "methods"]
        self._usr_params = ["id", "user_name", "user_surname", 
                    "email_addr", "greenhouse"]
        self._greenhouse_params = ['id', 'user_id', 'device_id' 'plant_type', 'plant_needs']
        self._services_params = ['id', 'name', 'endpoints', 'endpoints_details']

        # Default empty device catalog
        self._default_dev_cat = {
            "ip": "", "port": -1, "methods": []
            }
        
        self.out_path = out_path

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

    def getServCatInfo(self):
        return self.cat["services_catalog"]

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

    def getUsers(self):
        # Return the list of users
        return self.cat["users"]

    def getGreenhouses(self):
        return self.cat["greenhouses"]

    def getServices(self):
        return self.cat["services"]
    
    def getUserGreenhouses(self, userID):
        for usrinfo in self.cat["users"]:
            if usrinfo["id"] == int(userID):
                return usrinfo["greenhouses"]

    # COUNTERS
    def countUsers(self):
        return len(self.cat["users"])

    def countGreenhouses(self):
        return len(self.cat["greenhouses"])
    
    def countServices(self):
        return len(self.cat["services"])

    # SEARCHES: search for specific record

    def searchUser(self, parameter, value):
        if parameter not in self._usr_params:
            raise KeyError(f"Invalid key '{parameter}'")
        elem = {}
        for elem_cat in self.cat["users"]:
            if elem_cat[parameter] == value:
                # Supposing no duplicates
                elem = elem_cat.copy()
        
        return elem

    def searchGreenhouse(self, parameter, value):
        if parameter not in self._greenhouse_params:
            raise KeyError(f"Invalid key '{parameter}'")
        elem = {}
        for elem_cat in self.cat["greenhouses"]:
            if elem_cat[parameter] == value:
                elem = elem_cat.copy()

        return elem
    
    def searchService(self, parameter, value):
        if parameter not in self._services_params:
            raise KeyError(f"Invalid key '{parameter}'")
        elem = {}
        for elem_cat in self.cat["services"]:
            if elem_cat[parameter] == value:
                elem = elem_cat.copy()

        return elem

    # ADDERS: add new records

    def addDevCat(self, device_catalog):
        """ 
        Add device catalog info; if successful, the returned value
        is 1, else 0.
        No replacement! To update an existing element, consider
        `updateDevCat()`.

        If the returned value is 0, one of the following happened:
        - The inserted element does not contain the required fields
        - The device catalog was already added
        """
        if all(elem in device_catalog for elem in self._dev_cat_params):
            if self.cat["device_catalog"]["last_update"] == "":
                # The object was not created yet
                for key in self._default_dev_cat:
                    # Doing this prevents to insert keys that are not the allowed ones
                    self.cat["device_catalog"][key] = device_catalog[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["device_catalog"]["last_update"] = self.last_update
                self.cat["last_update"] = self.last_update
                return 1
        return 0

    def addUser(self, newUsr):
        """ 
        Add new user; if successful, the returned value
        is the new element ID, else 0.
        No replacement! To update an existing element, consider
        `updateUser()`.

        If the returned value is 0, one of the following happened:
        - The inserted element does not contain the required fields
        - An element with the same ID already exists

        This method also prevents to add elements having unnecessary keys
        """
        
        if all(elem in newUsr for elem in self._usr_params):
            # can proceed to adding the element
            new_id = newUsr["id"]
            if self.searchUser("id", new_id) == {}:
                # not found
                new_dict = {}
                for key in self._usr_params:
                    new_dict[key] = newUsr[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_dict["last_update"] = self.last_update
                self.cat["users"].append(new_dict)
                self.cat["last_update"] = self.last_update
                return new_id

        return 0    # Element is either invalid or already exists

    def addGreenhouse(self, newGH):
        """ 
        Add new greenhouse; if successful, the returned value
        is the new element ID, else 0.
        No replacement! To update an existing element, consider
        `updateGreenhouse()`.

        If the returned value is 0, one of the following happened:
        - The inserted element does not contain the required fields
        - An element with the same ID already exists

        This method also prevents to add elements having unnecessary keys
        """
        if all(elem in newGH for elem in self._greenhouse_params):
            # can proceed to adding the element
            new_id = newGH["id"]
            if self.searchGreenhouse("id", new_id) == {}:
                new_dict = {}
                for key in self._greenhouse_params:
                    new_dict[key] = newGH[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_dict["last_update"] = self.last_update
                self.cat["greenhouses"].append(new_dict)
                self.cat["last_update"] = self.last_update
                return new_id
        
        return 0

    def addService(self, newServ):
        """ 
        Add new service; if successful, the returned value
        is the new element ID, else 0.
        No replacement! To update an existing element, consider
        `updateService()`.

        If the returned value is 0, one of the following happened:
        - The inserted element does not contain the required fields
        - An element with the same ID already exists

        This method also prevents to add elements having unnecessary keys
        """
        if all(elem in newServ for elem in self._services_params):
            # can proceed to adding the element
            new_id = newServ["id"]
            if self.searchService("id", new_id) == {}:
                new_dict = {}
                for key in self._services_params:
                    new_dict[key] = newServ[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_dict["last_update"] = self.last_update
                self.cat["services"].append(new_dict)
                self.cat["last_update"] = self.last_update
                return new_id
        
        return 0


    # UPDATERS: update records
    
    def updateDevCat(self, upd_info):
        if all(elem in upd_info for elem in self._dev_cat_params):
            if self.cat["device_catalog"]["last_update"] != "":
                # The object already existed
                for key in self._default_dev_cat:
                    # Doing this prevents to insert keys that are not the allowed ones
                    self.cat["device_catalog"][key] = upd_info[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["device_catalog"]["last_update"] = self.last_update
                self.cat["last_update"] = self.last_update
                return 1
        return 0

    def updateUser(self, updUsr):
        # Check fields
        if all(elem in updUsr for elem in self._usr_params):
            # Find device
            for ind in range(len(self.cat["users"])):
                if self.cat["users"][ind]["id"] == updUsr["id"]:
                    for key in self._usr_params:
                        self.cat["users"][ind][key] = updUsr[key]
                    self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cat["users"][ind]["last_update"] = self.last_update
                    self.cat["last_update"] = self.last_update
                    return updUsr["id"]
            
        return 0

    def updateGreenhouse(self, upd_gh):
        if all(elem in upd_gh for elem in self._greenhouse_params):
            # Find greenhouse
            for ind in range(len(self.cat["greenhouses"])):
                if self.cat["greenhouses"][ind]["id"] == upd_gh["id"]:
                    for key in self._greenhouse_params:
                        self.cat["greenhouses"][ind][key] = upd_gh[key]
                    self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cat["greenhouses"][ind]["last_update"] = self.last_update
                    self.cat["last_update"] = self.last_update
                    return upd_gh["id"]
            
        return 0

    def updateService(self, upd_ser):
        if all(elem in upd_ser for elem in self._services_params):
            # Find service
            for ind in range(len(self.cat["services"])):
                if self.cat["services"][ind]["id"] == upd_ser["id"]:
                    for key in self._services_params:
                        self.cat["services"][ind][key] = upd_ser[key]
                    self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cat["services"][ind]["last_update"] = self.last_update
                    self.cat["last_update"] = self.last_update
                    return upd_ser["id"]
            
        return 0

    # CLEANERS: perform timeout check on records

    def cleanDevCat(self, curr_time, timeout):
        """
        Clean up device catalog records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        try:
            oldtime = datetime.timestamp(datetime.strptime(self.cat["device_catalog"]["last_update"], "%Y-%m-%d %H:%M:%S"))
        except:
            # If unable to read timestamp it means it is empty
            return 0
        if curr_time - oldtime > timeout:
            self.cat["device_catalog"] = self._default_dev_cat
            self.cat["device_catalog"]["last_update"] = ""
            self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cat["last_update"] = self.last_update
            return 1
        
        return 0

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
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["last_update"] = self.last_update
                n_rem += 1
        
        return n_rem

    def cleanGreenhouses(self, curr_time, timeout):
        """
        Clean up old greenhouse records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        n_rem = 0
        for ind in range(len(self.cat["greenhouses"])):
            gh_time = datetime.timestamp(datetime.strptime(self.cat["greenhouses"][ind]["last_update"], "%Y-%m-%d %H:%M:%S"))
            if curr_time - gh_time > timeout:
                # Delete record
                self.cat["greenhouses"].remove(self.cat["greenhouses"][ind])
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["last_update"] = self.last_update
                n_rem += 1
        
        return n_rem

    def cleanServices(self, curr_time, timeout):
        """
        Clean up old service records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        n_rem = 0
        for ind in range(len(self.cat["services"])):
            gh_time = datetime.timestamp(datetime.strptime(self.cat["services"][ind]["last_update"], "%Y-%m-%d %H:%M:%S"))
            if curr_time - gh_time > timeout:
                # Delete record
                self.cat["services"].remove(self.cat["services"][ind])
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["last_update"] = self.last_update
                n_rem += 1
        
        return n_rem

    

class ServicesCatalogWebService():
    """
    ServicesCatalogWebService
    ---
    Used to open the service catalog to the public
    """
    exposed = True

    def __init__(self, catalog_path, cmd_list_cat, output_cat_path="serv_catalog_updated.json"):
        self.API = json.load(open(cmd_list_cat))
        self.catalog = ServicesCatalog(catalog_path, output_cat_path)
        self.msg_ok = {"status": "SUCCESS", "msg": ""}
        self.msg_ko = {"status": "FAILURE", "msg": ""}
        self.timeout = 120          # seconds

        self.my_info = self.catalog.getServCatInfo()

    def GET(self, *uri, **params):

        # Potential issue (2): when retrieving users, greenhouses or services, the returned
        # string is obtained from a list of dict (users) - although when performing json.loads()
        # on the string, Python can correctly detect a 'list' objects
        
        # Depending on uri path, show what is required
        if (len(uri) >= 1):
            if (str(uri[0]) == "projectInfo"):
                # Return project info
                p_name = json.dumps(self.catalog.gerProjectName())
                p_owner = json.dumps(self.catalog.gerProjectOwner())
                return f"{p_name}, by {p_owner}"
            elif (str(uri[0]) == "broker"):
                # Return broker info
                return json.dumps(self.catalog.getBroker())
            elif (str(uri[0]) == "telegram"):
                return json.dumps(self.catalog.getTelegram())
            elif (str(uri[0]) == "device_catalog"):
                return json.dumps(self.catalog.getDevCatalog())
            
            elif (str(uri[0]) == "users"):
                # Return info of all users
                return json.dumps(self.catalog.getUsers())
            elif (str(uri[0]) == "user"):
                # Return info of specified user
                if "id" in params:
                    usr_ID = int(params["id"])
                    usr_found = self.catalog.searchUser("id", usr_ID)
                    if usr_found != {}:
                        return json.dumps(usr_found)
                    else:
                        raise cherrypy.HTTPError(404, f"User {usr_ID} not found")
                else:
                    raise cherrypy.HTTPError(400, "Missing/wrong parameters")
            
            elif (str(uri[0]) == "greenhouses"):
                if len(params) == 0:
                    return json.dumps(self.catalog.getGreenhouses())
                else:
                    if len(params) == 1 and str(params.keys()[0]) == 'id':
                        usr_ID = int(params["id"])
                        out_gh = self.catalog.getUserGreenhouses(usr_ID)
                        if out_gh == {}:
                            raise cherrypy.HTTPError(404, f"User {usr_ID} not found")
                        else:
                            return json.dumps(out_gh)
                    else:
                        raise cherrypy.HTTPError(400, "Missing/wrong parameters")
            elif (str(uri[0]) == "greenhouse"):
                if "id" in params:
                    gh_ID = int(params["id"])
                    gh_found = self.catalog.searchGreenhouse("id", gh_ID)
                    if gh_found != {}:
                        return json.dumps(gh_found)
                    else:
                        raise cherrypy.HTTPError(404, f"Greenhouse {gh_ID} not found")
                else:
                    raise cherrypy.HTTPError(400, "Missing/wrong parameters")

            elif (str(uri[0]) == "services"):
                return json.dumps(self.catalog.getServices())
            elif (str(uri[0]) == "service"):
                s_found = {}
                s_obj = None
                if len(params) > 0:
                    if "id" in params:
                        s_obj = int(params["id"])
                        s_found = self.catalog.searchService("id", s_obj)
                    elif "name" in params:
                        s_obj = str(params["name"])
                        s_found = self.catalog.searchService("name", s_obj)
                    
                    if s_found != {}:
                        # Object was correctly found
                        return json.dumps(s_found)
                    elif s_obj is not None:
                        # Object was understood but not found
                        raise cherrypy.HTTPError(404, f"Service {s_obj} not found")
                
                # Missing required params
                else:
                    raise cherrypy.HTTPError(400, "Missing/wrong parameters")

        else:       # Default case
            return "Available commands: " + json.dumps(self.API["methods"][0])

    def POST(self, *uri, **params):
        """ 
        Used to add new records (users/devices)
        """
        body = json.loads(cherrypy.request.body.read()) # Dictionary

        if (len(uri) >= 1):
            if (str(uri[0]) == "device_catalog"):
                if self.catalog.addDevCat(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Device catalog was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add device catalog"
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
            
            elif (str(uri[0]) == "greenhouse"):
                if self.catalog.addGreenhouse(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Greenhouse " + str(body["id"]) + " was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add greenhouse"
                    cherrypy.response.status = 400
                    return json.dumps(out)
            
            elif (str(uri[0]) == "service"):
                if self.catalog.addService(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Service " + str(body["id"]) + " was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add service"
                    cherrypy.response.status = 400
                    return json.dumps(out)
        
        else:
            return "Available commands: " + json.dumps(self.API["methods"][1])

    def PUT(self, *uri, **params):
        """
        Used to update existing records
        Use it at refresh (when services/devices keep updated the register)
        """
        body = json.loads(cherrypy.request.body.read())

        if (len(uri) >= 1):
            if (str(uri[0]) == "device_catalog"):
                if self.catalog.updateDevCat(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Device catalog was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update device catalog"
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
        
        elif (str(uri[0]) == "greenhouse"):
                if self.catalog.updateGreenhouse(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Greenhouse " + str(body["id"]) + " was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update greenhouse"
                    cherrypy.response.status = 400
                    return json.dumps(out)

        elif (str(uri[0]) == "services"):
                if self.catalog.updateService(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = "Service " + str(body["id"]) + " was updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update service"
                    cherrypy.response.status = 400
                    return json.dumps(out)

        return "Available commands: " + json.dumps(self.API["methods"][2])

    ############ Private methods ###################

    def cleanRecords(self):
        ## Check for old records (> 2 min)
        curr_time = time.time()

        rem_d = self.catalog.cleanDevCat(curr_time, self.timeout)
        rem_u = self.catalog.cleanUsers(curr_time, self.timeout)
        rem_gh = self.catalog.cleanGreenhouses(curr_time, self.timeout)
        rem_s = self.catalog.cleanServices(curr_time, self.timeout)
        
        if rem_d > 0 or rem_u > 0 or rem_gh > 0 or rem_s > 0:
            self.catalog.saveAsJson()

        print(f"\n%%%%%%%%%%%%%%%%%%%%\nRemoved {rem_d+rem_u+rem_gh+rem_s} element(s)\n%%%%%%%%%%%%%%%%%%%%\n")

    def cleanupLoop(self, refresh_rate):
        while True:
            time.sleep(refresh_rate)
            self.cleanRecords()


    def getMyIP(self):
        return self.my_info["ip"]

    def getMyPort(self):
        return self.my_info["port"]

#
#
#
#
#

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True
        }
    }

    # Ideally in the final application the initial catalog is passed to the 
    # application a a parameter, to allow users to use their own file and prevent
    # from storing cleartext paswords
    if len(sys.argv) > 1:
        WebService = ServicesCatalogWebService(sys.argv[1], "cmdList.json")
    else:
        WebService = ServicesCatalogWebService("serv_catalog.json", "cmdList.json")

    cherrypy.tree.mount(WebService, '/', conf)
    cherrypy.config.update({'server.socket_host': WebService.getMyIP()})
    cherrypy.config.update({'server.socket_port': WebService.getMyPort()})
    cherrypy.engine.start()
    WebService.cleanupLoop(30)
    
    # This part is not executed
    cherrypy.engine.block()
