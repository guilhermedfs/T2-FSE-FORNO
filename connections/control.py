import RPi.GPIO as GPIO

class Control:
    def __init__(self, port_r, port_v):
        self.port_r = port_r
        self.port_v = port_v
        
        self.setup()
        
    def setup(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.port_r, GPIO.OUT)
        GPIO.setup(self.port_v, GPIO.OUT)
        
        self.resistence = GPIO.PWM(self.port_r, 1000)
        self.resistence.start(0)
        
        self.vent = GPIO.PWM(self.port_v, 1000)
        self.vent.start(0)
        
    def warm(self, pid):
        self.resistence.ChangeDutyCycle(pid)
        
    def cool(self, pid):
        self.vent.ChangeDutyCycle(pid)
        
        
    