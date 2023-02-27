import paho.mqtt.client as PahoMQTT
import json
import time


def notify(topic, payload):
    # Suppose JSON
    print(f"Published in topic {topic}:\n{payload}")

class MyClient():
    def __init__(self, cl_ID, broker_add, port):
        self.broker_add = broker_add
        self.port = port
        # self.notifier = notifier
        self.clID = cl_ID
        self._topics_sub = ""
        self._isSub = False

        self._paho_cli = PahoMQTT.Client(cl_ID, True)

        ##### Callbacks:
        self._paho_cli.on_connect = self.myOnConn
        self._paho_cli.on_message = self.myOnMsgRx
        self._paho_cli.on_publish = self.myOnPub


    def myOnConn(self, clnt, userdata, flags, rc):
        print(f"Connected to broker, with result code {rc}!")

    def myOnMsgRx(self, clnt, userdata, msg):
        notify(msg.topic, msg.payload)

    def myOnPub(self, clnt, userdata, mid):
        # mid: message ID
        print(f"Message {mid} has been delivered")

#
    def myPub(self, topic, msg):
        self._paho_cli.publish(topic, json.dumps(msg), qos=2)

    def mySub(self, topic):
        self._topics_sub = topic
        self._paho_cli.subscribe(topic=topic, qos=2)
        self._isSub = True
        print(f"Subscribed to {topic}")
#
#

if __name__ == '__main__':
    cli_id = 'dmacario1'
    broker_add = 'mqtt.eclipseprojects.io'
    broker_port = 1883
    topic_sub = 'smartGreenhouse/1/+/temperature'
    topic_pub = 'smartGreenhouse/1/act_water'

    
    msg1 = {"cmd": "start", "t":""}
    msg2 = {"cmd": "stop", "t":""}

    clnt = MyClient(cl_ID=cli_id, broker_add=broker_add, port=broker_port)

    clnt._paho_cli.connect(host=broker_add, port=broker_port)

    time.sleep(5)

    clnt.mySub(topic=topic_sub)

    clnt._paho_cli.loop_start()

    ind = 0
    while True:
        time.sleep(5)
        print(".")
        if ind%2 == 0:
            msg_now = msg1.copy()
            msg_now["t"] = time.time()
            clnt.myPub(
                topic=topic_pub, 
                msg=msg_now
                )
            ind += 1
        else:
            msg_now = msg2.copy()
            msg_now["t"] = time.time()
            clnt.myPub(
                topic=topic_pub, 
                msg=msg_now
                )
            ind = 0
            
