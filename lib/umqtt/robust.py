import time
from . import simple


class MQTTClient(simple.MQTTClient):
    DELAY = 2
    DEBUG = False

    def delay(self, i):
        time.sleep(self.DELAY)

    def log(self, in_reconnect, e):
        if self.DEBUG:
            if in_reconnect:
                print("mqtt reconnect: %r" % e)
            else:
                print("mqtt: %r" % e)

    def reconnect(self):
        i = 0
        while 1:
            try:
                res = super().connect(False)
                if hasattr(self, 'subscriptions'):
                    for topic, qos in self.subscriptions:
                        super().subscribe(topic, qos)
                return res
            except OSError as e:
                self.log(True, e)
                i += 1
                self.delay(i)

    def subscribe(self, topic, qos=0):
        if not hasattr(self, 'subscriptions'):
            self.subscriptions = []
        sub = (topic, qos)
        if sub not in self.subscriptions:
            self.subscriptions.append(sub)
        return super().subscribe(topic, qos)

    def publish(self, topic, msg, retain=False, qos=0):
        while 1:
            try:
                return super().publish(topic, msg, retain, qos)
            except OSError as e:
                self.log(False, e)
            self.reconnect()

    def wait_msg(self):
        while 1:
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
            self.reconnect()

    def check_msg(self, attempts=2):
        while attempts:
            self.sock.setblocking(False)
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
            self.reconnect()
            attempts -= 1
