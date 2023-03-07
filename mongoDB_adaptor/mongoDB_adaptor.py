import pymongo
import json
import datetime  


class mongoAdaptor():
    
    def __init__(self, url_database,database_name, collection_name):
        self.myclient = pymongo.MongoClient(url_database)
        self.mydb = self.myclient[database_name]
        self.mycol = self.mydb[collection_name]
        self.collection = collection_name
        
#-------------------------------------------------------------------------------------
# ADMIN METHOD:
    
    #################################################################################
    # This method can be used by the administator only (no REST interface) to delete#
    # all the elements in a collection                                              #
    #################################################################################
    def remove_all_doc(self):
        self.mycol.delete_many({})
    
    
    #################################################################################
    # This method can be used by the administator only (no REST interface) to insert#
    # all the elements in a json file                                               #
    #################################################################################
    def insert_from_file_json(self,file_name):
        dict = json.load(open(file_name))
        self.mycol.insert_many(dict["data"])
    
    
#-------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------
# USER METHODS:

    #################################################################################
    # The two following methods can be used to add one or more elements in the      #
    # "weather" collection                                                          #
    #################################################################################
    def insert_one_dict(self, dict):
        if self.collection == "plants":
            raise KeyError("Request in wrong collection")
        elif self.collection == "weather":
            # When we insert a new record we add the timestamp
            now = datetime.datetime.now()
            dict["timestamp"]=datetime.datetime.strptime(now.strftime("%Y-%m-%d"),"%Y-%m-%d")
            self.mycol.insert_one(dict)        
    
    
    def insert_many_dict(self,m_dict):
        if self.collection == "plants":
            raise KeyError("Request in wrong collection")
        elif self.collection == "weather":
            tmp_list=[]
            now = datetime.datetime.now()
            for val in m_dict:
                val["timestamp"]=datetime.datetime.strptime(now.strftime("%Y-%m-%d"),"%Y-%m-%d")
                tmp_list.append(val)
            self.mycol.insert_many(tmp_list)
        
 
    #################################################################################
    # It searches the plant with the specified id.                                  #                
    #                                                                               #
    # It returns all the information related to the plant (it's the only method with#
    # the name search).                                                             #
    #################################################################################
    def find_by_id(self,id):
        myquery = { "_id": id }        
        cur=self.mycol.find(myquery)
        for doc in cur:
            val = str(doc)
            val = val.replace('\'','\"')
        return val
    
    
    #################################################################################
    # It searches the plant with the specified name                                 #                
    #                                                                               #
    # It returns all the information related to the plant (it's the only method with# 
    # the id search).                                                               #
    #################################################################################    
    def find_by_name(self,name):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            myquery = { "name": name }        
            cur=self.mycol.find(myquery).limit(1)
        for doc in cur:
            val = str(doc)
            val = val.replace('\'','\"')
        return val
        
    
    #################################################################################
    # This method returns the needs of a plant given the ID                         #
    #################################################################################
    def find_by_id_needs(self,id):
        myquery = { "_id": id }        
        cur=self.mycol.find(myquery)
        for doc in cur:
            val = str(doc)
            val = val.replace('\'','\"') 
        # val it's a string so we have to change it to dictionary
        dict = json.loads(val)
        needs_dict = {"needs":[]}
        listKeys = dict.keys()
        listKeys=list(listKeys)
        
        # cicle to fill the main key and its value
        for i in range(13,len(listKeys)):
            needs_dict["needs"].append({listKeys[i]:dict[listKeys[i]],"unit":""})
        measure_unit=["lumen","°C","g/m3"]
        
        # cicle for to fill the unit field of the dictionary
        for i in range(len(needs_dict["needs"])):
            if i<2:
                needs_dict["needs"][i]["unit"]=measure_unit[0]
            elif i<4:
                needs_dict["needs"][i]["unit"]=measure_unit[1]
            else:
                needs_dict["needs"][i]["unit"]=measure_unit[2]
        return json.dumps(needs_dict)

        
    #################################################################################
    # It searches the first N plants that belong to the specified category          #
    #                                                                               #
    # It returns a list of plants. The id and name only {"_id":id},{"name":name}).  #
    #################################################################################
    def find_by_category(self,category, N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            cursor = self.mycol.find({"category":category},{"name":1}).limit(N)
            tmp_list=[]
            for val in cursor:
                val=str(val)
                val = val.replace('\'','\"')
                tmp_list.append(val)
            return (tmp_list)
    
    
    #################################################################################
    # It Searches the first N plants thet have a volume between min_size and        #
    # max_size the volume is calculated as: 3.14*d^(2)*h/4, where it is a cylinder  #
    # volume, d is the diameter of the base, h the height.                          #
    #                                                                               #
    # The database is expected correct                                              #
    #                                                                               #
    # The method returns the list of dictionaries ({"_id":id},{"name":name}) of the # 
    # all (max N) plants selected.                                                  #
    #################################################################################
    def find_by_size(self,min_size,max_size, N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            list_correct = []
            count=0
            for i in range(len(list(self.mycol.find()))):
                val_cursor = self.mycol.find({ "_id": i},{"name":1,"size":1})
                for doc in val_cursor:
                    val = str(doc)
                    val = val.replace('\'','\"')
                val = json.loads(val)
                values_list = val["size"]
                volume = 3.14*values_list[0]*values_list[0]*values_list[1]/4
                if volume> min_size and volume <max_size:
                    val.pop("size", None)
                    list_correct.append(val)
                    count+=1
                if count == N:
                    break
            return (list_correct)
    
    
    #################################################################################
    # The method searches the first N plants that survive at a specific temperature #
    #                                                                               #
    # The method returns the list of dictionaries ({"_id":id},{"name":name}) of the # 
    # all (max N) plants selected.                                                  #
    #################################################################################
    def find_by_temperature(self, temperature, N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            list_correct = []
            count=0
            for i in range(len(list(self.mycol.find()))):
                val_cursor = self.mycol.find({ "_id": i},{"name":1,"min_temp":1,"max_temp":1})
                for doc in val_cursor:
                    val = str(doc)
                    val = val.replace('\'','\"')
                val = json.loads(val)
                if temperature > val["min_temp"] and temperature < val["max_temp"]:
                    val.pop("min_temp", None)
                    val.pop("max_temp", None)
                    list_correct.append(val)
                    count+=1
                if count==N:
                    break               
        return (list_correct)
    
    
    #################################################################################
    # The method searches the first N plants that survive at a specific humidity. So#
    # it controls if it is in the range between min and max humidity                #
    #                                                                               #
    # The method returns the list of dictionaries ({"_id":id},{"name":name}) of the # 
    # all (max N) plants selected.                                                  #
    #################################################################################
    def find_by_humidity(self,humidity,N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            list_correct = []
            count=0
            for i in range(len(list(self.mycol.find()))):
                val_cursor = self.mycol.find({ "_id": i},{"name":1,"min_env_humid":1,"max_env_humid":1})
                for doc in val_cursor:
                    val = str(doc)
                    val = val.replace('\'','\"')
                val = json.loads(val)
                if humidity > val["min_env_humid"] and humidity < val["max_env_humid"]:
                    val.pop("min_env_humid", None)
                    val.pop("max_env_humid", None)
                    list_correct.append(val)
                    count+=1
                if count==N:
                    break 
        return (list_correct)
    
    
    #################################################################################
    # The method searches the first N plants that survive at a specific quantity of #
    # luminosity measured in lux. So it controls if the light is in the range       #
    # between min and max lux.                                                      #
    #                                                                               #
    # The method returns the list of dictionaries ({"_id":id},{"name":name}) of the # 
    # all (max N) plants selected.                                                  #
    #################################################################################
    def find_by_lux(self, lux, N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants":
            list_correct = []
            count=0
            for i in range(len(list(self.mycol.find()))):
                val_cursor = self.mycol.find({ "_id": i},{"name":1,"min_light_lux":1,"max_light_lux":1})
                for doc in val_cursor:
                    val = str(doc)
                    val = val.replace('\'','\"')
                val = json.loads(val)
                if lux > val["min_light_lux"] and lux < val["max_light_lux"]:
                    val.pop("min_light_lux", None)
                    val.pop("max_light_lux", None)
                    list_correct.append(val)
                    count+=1
                if count==N:
                    break 
        return  (list_correct)
    
    
    #################################################################################
    # The method controls the moisture concentration and it must be inside the      #
    # survival range of the plant.                                                  #
    #                                                                               #
    # The method returns the list of dictionaries ({"_id":id},{"name":name}) of the # 
    # all (max N) plants selected.                                                  #
    #################################################################################
    def find_by_moisture(self,moist, N):
        if self.collection == "weather":
            raise KeyError("Request in wrong collection")
        elif self.collection == "plants": 
            list_correct = []
            count=0
            for i in range(len(list(self.mycol.find()))):
                val_cursor = self.mycol.find({ "_id": i},{"name":1,"min_soil_moist":1,"max_soil_moist":1})
                for doc in val_cursor:
                    val = str(doc)
                    val = val.replace('\'','\"')
                val = json.loads(val)
                if moist > val["min_soil_moist"] and moist < val["max_soil_moist"]:
                    val.pop("min_soil_moist", None)
                    val.pop("max_soil_moist", None)
                    list_correct.append(val)
                    count+=1
                if count==N:
                    break 
        return (list_correct)
    
    
    #################################################################################
    # Given a data it return the record of that data if present.                    #
    #################################################################################
    def find_by_timestamp(self, timestamp):
        if self.collection == "plants":
            raise KeyError("Request in wrong collection")
        elif self.collection == "weather":
            timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d')
            myquery = { "timestamp": timestamp }
            return self.mycol.find(myquery)
    
    
    #################################################################################
    # This method returns the records that belong to a time gap [min_date, max_date]#
    #                                                                               #
    # Remember that the object related by the key "date" is a datatime object       #
    #################################################################################
    def find_by_range_timestamp(self, min_date, max_date):
        if self.collection == "plants":
            raise KeyError("Request in wrong collection")
        elif self.collection == "weather":
            min = datetime.datetime.strptime(min_date, '%Y-%m-%d')
            max = datetime.datetime.strptime(max_date, '%Y-%m-%d')
            cursor = self.mycol.find({"timestamp": {"$gt": min,"$lt":max}})
            tmp_list=[]
            for val in cursor:
                val=str(val)
                val = val.replace('\'','\"')
                tmp_list.append(val)
            return (tmp_list)
    
    
    #################################################################################
    # The method deletes all the records with a timestamp before the given data     #
    #################################################################################
    def delete_before(self, date):
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        self.mycol.delete_many({"timestamp": {"$lt":date}})
#-------------------------------------------------------------------------------------
    
    

if __name__ == "__main__":
    url = "mongodb+srv://2BDM:Gruppo17@2bdm.bxvbkre.mongodb.net/"
    mongo = mongoAdaptor(url,"IOT_project","plants")
    mongo.remove_all_doc()
    #manyDict = {"index": 0,"name": "Abelia chinensis","image": "http://pkb.resource.huahuacaocao.com/YWJlbGlhIGNoaW5lbnNpcy5qcGc=?imageView2/1/w/%d/h/%d","origin": "China","category": "Caprifoliaceae, Abelia","blooming": "Flowering period July-August, fruiting period October","color": "Flower color pink, white","size": "Diameter \u00e2\u0089\u00a5 10 cm, height \u00e2\u0089\u00a5 15 cm","soil": "Peat or soil with specific nutrients","sunlight": "Like sunshine, slightly resistant to half shade","watering": "Water thoroughly when soil is dry, avoid saturated water","fertilization": "Dilute fertilizers following instructions, apply 1-2 times monthly","pruning": "Remove dead, rotten, diseased leaves and the parts that may affect the good appearance","max_light_lux": 30000,"min_light_lux": 3500,"max_temp": 35,"min_temp": 8,"max_env_humid": 85,"min_env_humid": 30,"max_soil_moist": 60,"min_soil_moist": 15}
    #mongo.insert_one_dict({"TMEDIA \u00b0C": 2, "TMIN \u00b0C": -3,  "TMAX \u00b0C": 6, "UMIDITA %": 63, "PRESSIONESLM mb": 1018, "FENOMENI": 0 })
    mongo.insert_from_file_json("new")
    #x= mongo.find_by_range_timestamp('2020-06-01', '2022-12-30')
    #x = mongo.find_by_timestamp('2022-12-27')
    #mongo.delete_before('2022-12-28')
    #print(list(x))
    """
    print("--------")
    x = mongo.find_by_temperature(20,1)
    for i in x:
        print(i)
    print("--------")
    x = mongo.find_by_humidity(32,1)
    for i in x:s
        print(i)
    print("--------")
    x = mongo.find_by_lux(5000,1)
    for i in x:
        print(i)
    print("--------")
    x = mongo.find_by_moisture(20,1)
    """
    #for i in x:
     #   print(i)