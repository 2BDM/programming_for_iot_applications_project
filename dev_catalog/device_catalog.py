import cherrypy
import requests
import json
import time
from datetime import datetime
import sys

"""
Device Catalog
---------------------------------------
This program contains the Device 
Catalog for our application 
---------------------------------------
Running on localhost, need to change 
port if running along the service 
catalog (on port 8080)
"""

class DeviceCatalog():
    """
    DeviceCatalog
    ---------------------------------------
    This class defines the main methods and
    attributes of the device catalog.
    The web service will use an instance of
    DeviceCatalog to handle the JSON 
    catalog.
    """

    def __init__(self, in_path, out_path="dev_catalog_updated.json"):
        # NOTE: this class does not need the static info about the services catalog
        # since connection to the services catalog is handled by the web service
        
        # Allow to use fac-simile catalog for testing
        try:
            self.cat = json.load(open(in_path))
        except:
            print("Default device catalog taken")
            self.cat = json.load(open("dev_catalog.json"))
        
        self._dev_cat_params = ['project_name', 'project_owner', 
                        'device_catalog', "devices"]

        # Check for valid catalog
        if all(elem for elem in self.cat for elem in self._dev_cat_params):
            print("Valid catalog!")
        else:
            raise KeyError("Wrong device catalog syntax!")
        
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cat["last_update"] = self.last_update

        # For checking at insertion:
        self._device_params = ['id', 'name', 'endpoints', 
                            'endpoints_details', 'greenhouse', 
                            'resources', 'last_update']
        
        self.out_path = out_path


    def saveAsJson(self):
        # Used to save a local copy of the current dictionary - returns 1 if success, else 0
        try:
            json.dump(self.cat, open(self.out_path, "w"))
            return 1
        except:
            return 0

    def getDevCatInfo(self):
        return self.cat["device_catalog"]

    def getDevices(self):
        return self.cat["devices"]

    def countDevices(self):
        return len(self.cat["users"])

    def searchDevice(self, parameter, value):
        if parameter not in self._device_params:
            raise KeyError(f"Invalid key '{parameter}'")
        elem = {}
        for elem_cat in self.cat["devices"]:
            if elem_cat[parameter] == value:
                elem = elem_cat.copy()

        return elem

    def addDevice(self, newDev):
        """ 
        Add new device; if successful, the returned value
        is the new element ID, else 0.
        No replacement! To update an existing element, consider
        `updateDevice()`.

        If the returned value is 0, one of the following happened:
        - The inserted element does not contain the required fields
        - An element with the same ID already exists

        This method also prevents to add elements having unnecessary keys
        """
        if all(elem in newDev for elem in self._device_params):
            # can proceed to adding the element
            new_id = newDev["id"]
            if self.searchDevice("id", new_id) == {}:
                new_dict = {}
                for key in self._device_params:
                    new_dict[key] = newDev[key]
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_dict["last_update"] = self.last_update
                self.cat["devices"].append(new_dict)
                self.cat["last_update"] = self.last_update
                return new_id
        
        return 0
    
    def updateDevice(self, upd_dev):
        if all(elem in upd_dev for elem in self._device_params):
            # Find service
            for ind in range(len(self.cat["devices"])):
                if self.cat["devices"][ind]["id"] == upd_dev["id"]:
                    for key in self._device_params:
                        self.cat["devices"][ind][key] = upd_dev[key]
                    self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cat["devices"][ind]["last_update"] = self.last_update
                    self.cat["last_update"] = self.last_update
                    return upd_dev["id"]
            
        return 0

    def cleanDevices(self, curr_time, timeout):
        """
        Clean up old devices records
        - curr_time: unix timestamp
        - timeout: in seconds
        """
        n_rem = 0
        for ind in range(len(self.cat["devices"])):
            gh_time = datetime.timestamp(datetime.strptime(self.cat["devices"][ind]["last_update"], "%Y-%m-%d %H:%M:%S"))
            if curr_time - gh_time > timeout:
                # Delete record
                self.cat["devices"].remove(self.cat["devices"][ind])
                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cat["last_update"] = self.last_update
                n_rem += 1
        
        return n_rem


class DeviceCatalogWebService():
    """
    DeviceCatalogWebService
    ---
    Used to open the device catalog to other application parts
    """

    exposed = True

    def __init__(self, catalog_path, serv_catalog_info="serv_cat_info.json", cmd_list_cat="cmd_list.json", output_cat_path="dev_catalog_updated.json"):
        self.API = json.load(open(cmd_list_cat))
        self.catalog = DeviceCatalog(in_path=catalog_path, out_path=output_cat_path)
        self.msg_ok = {"status": "SUCCESS", "msg": ""}
        self.msg_ko = {"status": "FAILURE", "msg": ""}
        self.timeout = 60          # seconds
        
        # Used for choosing when to try again to make POST to service catalog
        self.serv_timeout = 60

        self.my_info = self.catalog.getDevCatInfo()
        print(f"I am {self.my_info}")

        # TODO: Connect and register to service catalog
        # POST request
        try:
            self._serv_cat = json.load(open(serv_catalog_info))
        except:
            print("Default service catalog information taken!")
            self._serv_cat = json.open(open("serv_cat_info.json"))

        # For sure the service catalog is a WebService; get its address
        self._serv_cat_addr = "http://" + self._serv_cat["ip"]+':'+str(self._serv_cat["port"])
        
        # Register at the catalog
        self._registered_at_catalog = False
        self.registerAtCatalog()
    
        
    def GET(self, *uri, **params):
        if (len(uri) >= 1):
            if (str(uri[0]) == "devices"):
                return json.dumps(self.catalog.getDevices())
            elif (str(uri[0]) == "device"):
                if "id" in params:
                    dev_ID = int(params["id"])
                    found_dev = self.catalog.searchDevice("id", dev_ID)
                    if found_dev != {}:
                        # Was found
                        return json.dumps(found_dev)
                    else:
                        raise cherrypy.HTTPError(404, f"Device {dev_ID} not found!")
                elif "name" in params:
                    dev_name = str(params["name"])
                    found_dev = self.catalog.searchDevice("name", dev_name)
                    if found_dev != {}:
                        return json.dumps(found_dev)
                    else:
                        raise cherrypy.HTTPError(404, f"Device {dev_name} not found!")
                else:
                    raise cherrypy.HTTPError(400, f"Missing/wrong parameters")
        else:
            return "Available commands: " + json.dumps(self.API["methods"][0])

    def POST(self, *uri, **params):
        """ 
        Used to add new records (devices)
        """
        body = json.loads(cherrypy.request.body.read()) # Dictionary

        if (len(uri) >= 1):
            if (str(uri[0]) == "device"):
                if self.catalog.addDevice(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = f"Device {body['id']} was added"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 201
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to add device"
                    cherrypy.response.status = 400
                    return json.dumps(out)
        else:
            return "Available commands: " + json.dumps(self.API["methods"][1])

    def PUT(self, *uri, **params):
        """
        Used to update existing records
        Use it at refresh (when devices keep the register updated)
        """
        body = json.loads(cherrypy.request.body.read())

        if (len(uri) >= 1):
            if (str(uri[0]) == "device"):
                if self.catalog.updateDevice(body) != 0:
                    out = self.msg_ok.copy()
                    out["msg"] = f"Device {body['id']} was successfully updated"
                    self.catalog.saveAsJson()
                    cherrypy.response.status = 200
                    return json.dumps(out)
                else:
                    out = self.msg_ko.copy()
                    out["msg"] = "Unable to update device"
                    cherrypy.response.status = 400
                    return json.dumps(out)
        else:
            return "Available commands: " + json.dumps(self.API["methods"][2])


    ###########################################################

    def cleanRecords(self):
        curr_time = time.time()

        rem_d = self.catalog.cleanDevices(curr_time, self.timeout)

        if rem_d > 0:
            self.catalog.saveAsJson()

        print(f"\n%%%%%%%%%%%%%%%%%%%%\nRemoved {rem_d} device(s)\n%%%%%%%%%%%%%%%%%%%%\n")

    def registerAtCatalog(self):
        """
        This method is used to register the device catalog information
        on the service catalog.
        -----
        Return values:
        - 1: registration successful
        - -1: information was already present - update was performed
        - 0: update failed (unreachable server)
        """
        max_tries = 10
        tries = 0
        while not self._registered_at_catalog and tries < max_tries:
            try:
                reg = requests.post(self._serv_cat_addr + '/device_catalog', data=json.dumps(self.my_info))
                print(f"Sent request to {self._serv_cat_addr}")
                
                if reg.status_code == 201:
                    self._registered_at_catalog = True
                    self._last_update_serv = time.time()
                    print("Successfully registered at service catalog!")
                    return 1
                elif reg.status_code == 400:
                    print("Device catalog was already registered!")
                    self._registered_at_catalog = True
                    # Perform an update, to keep the last_update recent
                    self.updateServiceCatalog()
                    return -1
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                tries += 1
                time.sleep(5)
        
        if not self._registered_at_catalog:
            # If here, it was impossible to register/update info, hence the 
            # server was unresponsive/unreachable
            print("Maximum number of tries exceeded - server unreachable!")
            return 0

    def updateServiceCatalog(self):
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
        max_tries = 10

        while not updated and count_fail < max_tries:
            try:
                try1 = requests.put(self._serv_cat_addr + '/device_catalog', data=json.dumps(self.my_info))

                # If here, it was possible to send the request to the server (reachable)
                if try1.status_code == 200:
                    # Update successful
                    print("Information in the service catalog was successfully updated!")
                    self._last_update_serv = time.time()
                    return 1
                elif try1.status_code == 400:
                    print("Unable to update information at the service catalog ---> trying to register")
                    count_fail += 1
                    self._registered_at_catalog = False
                    self.registerAtCatalog()
                    if self._registered_at_catalog:
                        updated = True
                        return -1
            except:
                print("Tried to connect to services catalog - failed to establish a connection!")
                count_fail += 1
                time.sleep(5)
        
        # If here, then it was not possible to update nor register information
        # within the maximum number of iterations, which means it was not possible 
        # to reach the server
        print("Maximum number of tries exceeded - service catalog was unreachable!")
        return 0

    def startOperation(self, refresh_rate):
        # Begin looping to keep the service catalog updated and delete old device records
        while True:
            time.sleep(refresh_rate)
            self.updateServiceCatalog()
            time.sleep(5)
            self.cleanRecords()

    # Used to get information about IP and port n. from the 
    # device catalog settings json
    def getMyIP(self):
        return self.my_info["ip"]

    def getMyPort(self):
        return self.my_info["port"]

#
#
#
#
#
#

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }

    # It is possible to specify the path of the empty device catalog
    # or of the device catalog info as command line parameters
    if len(sys.argv) == 3:
        WebService = DeviceCatalogWebService(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        WebService = DeviceCatalogWebService(sys.argv[1])
    else:
        WebService = DeviceCatalogWebService("dev_catalog.json")

    cherrypy.tree.mount(WebService, '/', conf)
    cherrypy.config.update({'server.socket_host': WebService.getMyIP()})
    cherrypy.config.update({'server.socket_port': WebService.getMyPort()})
    cherrypy.engine.start()
    WebService.startOperation(30)