from MiniWebSrv import MiniWebSrv
from Config import Config
import json
import utime
import machine
import network


HTTP_RES_HEAD = b"""HTTP/1.1 200 OK
Content-Type: application/json;charset=utf-8
Connection: close

"""
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)


class WebConfig:
    def __init__(self, mqtt_conf, main_module=None, device_name='unknown'):
        self._device_name = device_name
        self._mqtt_conf = mqtt_conf
        self._leds_strip_conf = Config(filepath='leds_strip.json')

        routeHandlers = [( "/set_wifi", "POST", self._http_set_wifi ),
                         ( "/set_mqtt", "POST", self._http_set_mqtt ),
                         ( "/set_ap", "POST", self._http_set_ap ),
                         ( "/reboot", "POST", self._http_reboot ),
                         ( "/get_wifi", "GET", self._http_get_wifi ),
                         ( "/get_mqtt", "GET", self._http_get_mqtt ),
                         ( "/get_ap", "GET", self._http_get_ap ),
                         ( "/get_name", "GET", self._http_get_name ),
                         ( "/get_leds_strip", "GET", self._http_get_leds_strip ),
                         ( "/set_leds_strip", "POST", self._http_set_leds_strip ),
                         ]
        self._HttpServer = MiniWebSrv(routeHandlers=routeHandlers)
        self._data_changed=False

        if main_module:
            content = "import %s\n%s.start()\n"%(main_module,main_module)
            f = open('/main.py', 'w')
            f.write(content)
            f.flush()
            f.close()

    def start(self):
        if not self._HttpServer._started:
            ap_if.active(True)
            self._HttpServer.start()
            self._data_changed=False
    def stop(self):
        self._HttpServer.stop()
        ap_if.active(False)
        sta_if.active(True)

    @property
    def started(self):
        return self._HttpServer._started
    @property
    def data_changed(self):
        return self._data_changed

    def _http_set_wifi(self, c_socket, request_data):
        ssid = request_data.get("ssid")
        pwd = request_data.get("pwd")
        c = {}

        sta_if.active(True)
        sta_if.connect(ssid,pwd)

        i=0
        while not sta_if.isconnected():
            utime.sleep(1)
            i += 1
            if i>15:
                sta_if.active(False)
                break

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        self._data_changed=True


    def _http_set_mqtt(self, c_socket, request_data):
        c = {}

        try:
            from StateMQTTClient import StateMQTTClient
            port=1883
            try:
                port=int(request_data.get("mqtt_port"))
            except:
                print("MQTT Input port error, let it be 1883, and continue...")
            MqttClient = StateMQTTClient("testtest", request_data.get("mqtt_ip"), port=port, user=request_data.get("mqtt_user"), password=request_data.get("mqtt_password"), keepalive=60)
            MqttClient.connect()
            if MqttClient.connected:
                self._mqtt_conf.save( request_data )
                c['working']=True
                c['state_info']= [{'测试连接':'成功'},
                                  {'配置文件':'已保存'},
                                  ]
            else:
                c['working']=False
                c['state_info']= [{'测试连接':'失败'},
                                  {'配置文件':'未保存'},
                                  ]
                
            MqttClient.disconnect()
        except:
            c['working']=False
            c['state_info']= [{'测试连接':'异常'},
                              {'配置文件':'未保存'},
                              ]

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        self._data_changed=True
    
    def _http_set_ap(self, c_socket, request_data):
        c = {}

        ap_pwd = request_data.get("ap_pwd")
        ap_if.config( password = ap_pwd )

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        self._data_changed=True

    def _http_reboot(self, c_socket, request_data):
        c = {}

        c['working']=False
        c['state_info']= [{'当前状态':'重启……'}]

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        utime.sleep(1)
        ap_if.active(False)

        utime.sleep(3)
        machine.reset()


    def _http_get_wifi(self, c_socket, request_data):
        c = {}
        
        isconnected = sta_if.isconnected()

        if isconnected:
            ifconfig = sta_if.ifconfig()
            c['working']=True
            c['state_info']= [{'当前状态':'已连接'},
                              {'IP':ifconfig[0]},
                              {'网络掩码':ifconfig[1]},
                              {'网关':ifconfig[2]},
                              {'域名服务器':ifconfig[3]},
                              ]
        else:
            sta_if.active(False)
            c['working']=False
            c['state_info']= [{'当前状态':'未连接'},
                              ]
        
        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()

    def _http_get_mqtt(self, c_socket, request_data):
        c = {}

        if self._mqtt_conf.content:
            c = self._mqtt_conf.content

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        
    def _http_get_ap(self, c_socket, request_data):
        c = {}

        if ap_if.active():
            c['working']=True
            c['state_info']= [{'当前状态':'已打开'},
                              {'名称':ap_if.config('essid')},
                              ]
        else:
            c['working']=False
            c['state_info']= [{'当前状态':'AP未打开'},
                              ]
        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()

    def _http_get_name(self, c_socket, request_data):
        c = {}

        c['name'] = self._device_name

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()

    def _http_get_leds_strip(self, c_socket, request_data):
        c = {}

        if self._leds_strip_conf.content:
            c = self._leds_strip_conf.content

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall(json.dumps(c).encode())
        c_socket.close()        

    def _http_set_leds_strip(self, c_socket, request_data):
        c = {}

        self._leds_strip_conf.save( request_data )
        c['working']=True
        c['state_info']= [{'配置文件':'已保存'}]

        c_socket.sendall(HTTP_RES_HEAD)
        c_socket.sendall( json.dumps(c).encode())
        c_socket.close()
        self._data_changed=True

def toggle1():
    print("Apressed")
    
def start(pin_no, led_pin_no, main_module, device_name):
    from Irq_reset import Irq_reset
    from ubinascii import hexlify

    
    mqtt_conf = Config()

    webconfig = WebConfig(mqtt_conf=mqtt_conf, main_module=main_module, device_name=device_name)

    utime.sleep(10)
    webconfig.start()
    irq = Irq_reset(pin_no=14, led_pin_no=0,press_action=toggle1,main_module=main_module,device_name=device_name)
    while True:
        client, cliAddr = webconfig._HttpServer.accept()
        if client:
            webconfig._HttpServer.handle_client(client, cliAddr)
