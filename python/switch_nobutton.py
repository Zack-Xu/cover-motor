
from WebConfig import WebConfig
from Config import Config
from StateMQTTClient import StateMQTTClient
from ubinascii import hexlify
import network
import machine
import utime
import micropython
import sys

try:
    with open('counter.txt','r') as f:
        counter = int(f.read())
except:
    counter = 0

if counter>=4:
    RUN_MODE = 'config'
else:
    RUN_MODE = 'normal'


with open('counter.txt','w') as f:
    f.write(str(counter+1))
    f.flush()

def rm_counter(tim):
    with open('counter.txt','w') as f:
        f.write(str(0))
        f.flush()

timer = machine.Timer(-1)
timer.init(period=10000, mode=machine.Timer.ONE_SHOT, callback=rm_counter)


ap_if = network.WLAN(network.AP_IF)
sta_if = network.WLAN(network.STA_IF)

LED_PIN = 2
LED = machine.Pin(LED_PIN,machine.Pin.OUT)

SWITCH_PIN_1 = 4
SWITCH_PIN_2 = 1

#SWITCH_1 = machine.Pin(SWITCH_PIN_1,machine.Pin.OUT)
SWITCH_2 = machine.Pin(SWITCH_PIN_2,machine.Pin.OUT)

ACTIVE_STATUS = 'OFF'

DEVICE_NAME = 'pilight_switch_' + hexlify(ap_if.config("mac")[-3:]).decode()

CONFIG_DATA_SCHEMA = """
{"name": "%s",
"command_topic": "%s",
"state_topic": "%s",
"availability_topic": "%s"}
"""

BASE_TOPIC = 'piliboard/' + DEVICE_NAME
AVAILABILITY_TOPIC = BASE_TOPIC + "/availability"
COMMAND_TOPIC = BASE_TOPIC + "/command"
STATE_TOPIC = BASE_TOPIC + "/state"

CONFIG_TOPIC = 'homeassistant/switch/piliboard/' + DEVICE_NAME + '/config'
CONFIG_DATA = CONFIG_DATA_SCHEMA % (DEVICE_NAME,
                                    COMMAND_TOPIC,
                                    STATE_TOPIC,
                                    AVAILABILITY_TOPIC,
                                    )

MqttClient = None
mqtt_conf = Config()

webconfig = WebConfig(mqtt_conf=mqtt_conf, main_module=None, device_name=DEVICE_NAME)




def mqtt_start():
    MqttClient.connect()
    if MqttClient.connected:
        print("mqtt connected: subto {b}".format(b=COMMAND_TOPIC))
        MqttClient.subscribe(COMMAND_TOPIC)
        MqttClient.publish( CONFIG_TOPIC, CONFIG_DATA.encode(), retain=True)
        MqttClient.publish( AVAILABILITY_TOPIC, b"online", retain=True)
        MqttClient.publish( STATE_TOPIC, ACTIVE_STATUS.encode(), retain=True )
        return True
    else:
        print("Can't connect to MQTT Broker")
        return False


def mqtt_cb(topic, msg):
    print((topic, msg))

    if webconfig.started:
        webconfig.stop()

    if topic==COMMAND_TOPIC.encode():
        if msg == b"ON":
            SWITCH_1.value(1)
            SWITCH_2.value(1)
            for i in range(500000):
                a = 1
            ACTIVE_STATUS = 'ON'
        elif msg == b"OFF":
            SWITCH_1.value(0)
            SWITCH_2.value(0)
            for i in range(500000):
                a = 1
            ACTIVE_STATUS = 'OFF'
            
        MqttClient.publish( STATE_TOPIC, ACTIVE_STATUS.encode(), retain=True )


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


def start():

    if(RUN_MODE=='config'):
        LED.value(0)
        ap_if.active(True)
        sta_if.active(True)
        webconfig.start()
        while True :
            if webconfig.started:
                client, cliAddr = webconfig._HttpServer.accept()
                if client:
                    webconfig._HttpServer.handle_client(client, cliAddr)
                    continue
        
    else:
        LED.value(1)
        ap_if.active(False)
        sta_if.active(True)

        last_try_time1 = 0
        last_try_time2 = 0
        last_resp_time = utime.time()

        if mqtt_init(mqtt_conf.content):
            utime.sleep(5)
            mqtt_start()
        else:
            print("mqtt_init failed")


    #    try:
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



    #    except KeyboardInterrupt:
    #        sys.exit()
    #    else:
    #        machine.reset()
