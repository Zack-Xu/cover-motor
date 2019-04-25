from machine import Pin
from machine import Timer
import network
import machine
import os
import utime

class Irq_reset:
    def __init__(self, pin_no=10, led_pin_no=13, press_action=None, main_module=None, device_name='unknown' ):
        self._pin_no = pin_no
        self._led_pin_no = led_pin_no
        self._reset_pin = Pin(pin_no, Pin.IN)
        self._show_pin = Pin(led_pin_no, Pin.OUT)
        self._press_action = press_action
        self._main_module = main_module
        self._device_name = device_name
        self._p0 = 5000
        self._p1 = 10000
        ap_if = network.WLAN(network.AP_IF)
        if ap_if.active()==True :
            self._show_pin.value(1)
            self._cb_before_reset = self._write_main2
        else:
            self._show_pin.value(0)
            self._cb_before_reset = self._write_main
        self._timer = Timer(-1)
        self._timer2 = Timer(-1)
        self._state = 0

        
        self._reset_pin.irq(trigger=Pin.IRQ_FALLING, handler=self._callback1)

    def _write_main(self):
        c = "import %s\n%s.start(pin_no=%d, led_pin_no=%d, main_module=\"%s\",device_name=\"%s\")\n"%(
            "WebConfig","WebConfig",self._pin_no, self._led_pin_no,self._main_module,self._device_name)
    
        f = open('main.py', 'w')
        f.write(c)
        f.flush()
        f.close()
        
                
    def _write_main2(self):
        c = "import switch_button\nswitch_button.start()"
        f = open('main.py', 'w')
        f.write(c)
        f.flush()
        f.close()
        


    def _callback1(self, p):
        print('pressed')
        self._state = 1
        self._reset_pin.irq(trigger=Pin.IRQ_RISING, handler=self._callback2)
        self._timer.init(period=self._p0, mode=Timer.ONE_SHOT, callback=self._cb_flashing)

    def _callback2(self, p):
        print('released')
        if self._state == 1:
            self._press_action()
        elif self._state == 2:
            if self._cb_before_reset:
                self._cb_before_reset()
            print("重新启动")
            machine.reset()
        elif self._state == 3:
            if self._cb_before_reset:
                self._cb_before_reset()
            ap_if = network.WLAN(network.AP_IF)
            ap_if.active(True)
            utime.sleep(2)
            ap_if.config(password='micropythoN')
            utime.sleep(2)
            print("完全重新启动")
            machine.reset()

        self._reset_pin.irq(trigger=Pin.IRQ_FALLING, handler=self._callback1)
        self._state= 0
        self._show_pin.value(0)
        self._timer.deinit()
        self._timer2.deinit()

        
    def _cb_flashing(self, tim):
        if self._state == 1:
            print("flashing")
            self._state = 2
            self._timer.init(period=self._p1, mode=Timer.ONE_SHOT, callback=self._cb_flashing)
            self._timer2.init(period=200, mode=Timer.PERIODIC, callback=self._cb_toggle)
        elif self._state == 2:
            print("fast flashing")
            self._state = 3
            self._timer2.init(period=100, mode=Timer.PERIODIC, callback=self._cb_toggle)

    def _cb_toggle(self, tim):
        self._show_pin.value(not self._show_pin.value())
