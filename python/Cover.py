from SimpleIO import Switch
from Config import Config
from StateMQTTClient import StateMQTTClient
from Irq_reset import Irq_reset
from ubinascii import hexlify
import network
import machine
import utime
import micropython

ap_if = network.WLAN(network.AP_IF)
sta_if = network.WLAN(network.STA_IF)

BUTTON_PIN = 10

RELAY_PIN_1 = 12
RELAY_PIN_2 = 5

LED_PIN=13


Position = 0
Set_postion = 100
STATUS = 0
## 0 close 1 open 2 stop
Payload_open = "OPEN"
Payload_close = "CLOSE"
Payload_stop = "STOP"
switch_1= machine.Pin(RELAY_PIN_1,machine.Pin.OUT)
switch_2= machine.Pin(RELAY_PIN_2,machine.Pin.OUT)

PROGRAM_NAME = 'Cover'
DEVICE_NAME = 'Pili_Cover' + hexlify(ap_if.config("mac")[-3:]).decode()+"_"

#DEVICENAME MQTT设备ID

# JSON格式转换？
CONFIG_DATA_SCHEMA = """
{"name": "%s",
"command_topic": "%s",
"position_topic": "%s",
"availability_topic": "%s",
"set_postion_topic":"%s"
}
"""

BASE_TOPIC = 'HA/cover/' + DEVICE_NAME

AVAILABILITY_TOPIC = BASE_TOPIC + "/availability"
COMMAND_TOPIC = BASE_TOPIC+ "/command"
POSITION_TOPIC = BASE_TOPIC + "/position"
SET_POSITION_TOPIC = BASE_TOPIC + "/set_position"

CONFIG_TOPIC = 'homeassistant/cover/' + DEVICE_NAME + '/config'



CONFIG_DATA = CONFIG_DATA_SCHEMA % (
                                    DEVICE_NAME,
                                    COMMAND_TOPIC,
                                    POSITION_TOPIC,
                                    AVAILABILITY_TOPIC,
                                    SET_POSITION_TOPIC
                                    )



MqttClient = None

mqtt_conf = Config()





def mqtt_start():
    MqttClient.connect()
    if MqttClient.connected:
        
      
        MqttClient.publish( CONFIG_TOPIC, CONFIG_DATA.encode(), retain=True)
        MqttClient.subscribe(SET_POSITION_TOPIC)
        MqttClient.subscribe(COMMAND_TOPIC)        
        MqttClient.publish( AVAILABILITY_TOPIC, b"online", retain=True)
        MqttClient.publish( POSITION_TOPIC,str(Position).encode(), retain=True )
        print("mqtt connected: subto {b}".format(b=COMMAND_TOPIC))
        return True
    else:
        print("Can't connect to MQTT Broker")
        return False


def mqtt_cb(topic, msg):
    print((topic, msg))

    if topic==COMMAND_TOPIC.encode():
        if msg == Payload_close.encode():
            STATUS = 0
            print('AB')
        elif msg == Payload_open.encode():
            STATUS = 1
            print('CD')
        elif msg == Payload_stop.encode():
            STATUS = 2
            print('EF')
    elif topic == SET_POSITION_TOPIC.encode():
        Set_postion = msg
        
    if STATUS == 0:
        switch_2.value(0)
        for i in range (10000):
            a =1
        switch_1.value(1)
        Position = 0
        MqttClient.publish( POSITION_TOPIC,str(Position).encode(),retain=True)
        print('1')
    elif STATUS == 1:
        switch_1.value(0)
        for i in range (10000):
            a =1
        switch_2.value(1)
        Position = 100
        MqttClient.publish( POSITION_TOPIC,str(Position).encode(),retain=True)
        print('2')
    elif STATUS == 2:
        print('3')
        switch_1.value(0)
        switch_2.value(0)
    

def mqtt_init(conf):
    global MqttClient

    if (conf == None) or not('mqtt_ip' in conf):
        MqttClient = StateMQTTClient(DEVICE_NAME, None)
        return False

    port=1883
    try:
        port=int(conf.get("mqtt_port"))
    except:
        print("MQTT Input port error, let it be 1883, and continue...")
        
    MqttClient = StateMQTTClient(DEVICE_NAME, conf.get("mqtt_ip"), port=port, user=conf.get("mqtt_user"), password=conf.get("mqtt_password"), keepalive=60)
    MqttClient.set_callback(mqtt_cb)
    MqttClient.set_last_will( AVAILABILITY_TOPIC, b"offline", retain=True)
    return True


def toggle1():
    print("button_pressed")


        



def start():
    last_try_time1 = 0
    last_try_time2 = 0
    last_resp_time = utime.time()
    ap_if.active(False)
    sta_if.active(True)
    irq = Irq_reset(pin_no=BUTTON_PIN, led_pin_no=LED_PIN, main_module=PROGRAM_NAME, press_action=toggle1, device_name=DEVICE_NAME)
    

   

    
    if mqtt_init(mqtt_conf.content):
        utime.sleep(5)
        mqtt_start()
    else:
        print("mqtt_init failed")
        return


    while True :
        if not sta_if.isconnected():
            print("Can't connect to WIFI")
            utime.sleep(3)

        elif not MqttClient.connected:
            now = utime.time()
            last_resp_time = now
            delta = now - last_try_time1
            if delta > 10:
                last_try_time1 = now
                mqtt_start()
                micropython.mem_info()

        else:
            if MqttClient.check_msg()==1:
                last_resp_time = utime.time()
            now = utime.time()
            if now-last_resp_time > 20:
                print("No mqtt ping response, disconnect it")
                MqttClient.disconnect()
                continue

            delta = now - last_try_time2
            if delta > 10:
                MqttClient.ping()
                last_try_time2 = now
                micropython.mem_info()
