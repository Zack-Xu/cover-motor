import machine
class Switch:
    def __init__(self, led_num=5):
        self._state = 'OFF'
        self._IO = machine.Pin(led_num, machine.Pin.OUT)
        self.turn_off()

    def turn_on(self):
        self._state = 'ON'
        self._IO.value(True)

    def turn_off(self):
        self._state = 'OFF'
        self._IO.value(False)

    def toggle(self):
        if self._state == 'ON':
            self.turn_off()
        else:
            self.turn_on()



