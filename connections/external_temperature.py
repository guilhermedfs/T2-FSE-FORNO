import smbus2
import bme280

class ExternalTemperature:
    def __init__(self):
        self.port = 1
        self.address = 0x76
    
    def setup(self):
        self.bus = smbus2.SMBus(self.port)
        self.calibrationParameters = bme280.load_calibration_params(bus, self.address)

    def getTemperature(self) -> any:
        data = bme280.sample(self.bus, self.address, self.calibrationParameters) 
        
        return data.temperature