import random as rnd

class DHT11Agent:
    def __init__(self):
        self.type = "DHT11"
        self.dict_temp_hum = {"humidity":0,"temperature":0}
        
    def take_measure(self):
        self.updateTemp()
        self.updateHum()
        return self.dict_temp_hum
    
    def updateTemp(self):
        self.dict_temp_hum["temperature"]=rnd.randint(18,25)
        
    
    def updateHum(self):
        self.dict_temp_hum["humidity"]=rnd.randint(50,80)    