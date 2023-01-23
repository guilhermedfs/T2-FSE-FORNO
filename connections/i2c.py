import smbus2
import bme280

class I2C: 
    def __init__(self):
        self.port = 1
        self.address = 0x76
        self.configureBus()
        
    def configureBus(self):
        self.bus = smbus2.SMBus(self.port)
        
    def getExternalTemperature(self):
        calib_params = bme280.load_calibration_params(self.bus, self.address)
        
        data = bme280.sample(self.bus, self.address, calib_params)
        
        temperature = data.temperature
        
        return temperature