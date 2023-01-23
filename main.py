import serial
import time
import datetime
import struct
import math

from threading import Event, Thread

from connections.uart import UART
from utils.pid import PID
from connections.control import Control
from connections.i2c import I2C

class ReflowOven:
    def __init__(self):
        self.createVariables()
        self.createEvents()
        self.uart = UART(self.port, self.baudrate, self.timeout)
        self.pid = PID()
        self.control = Control(self.resistencePort, self.ventPort)
        self.i2c = I2C()
        self.startServices()
        
    def createVariables(self):
        self.port = '/dev/serial0'
        self.resistencePort = 23
        self.ventPort = 24
        self.baudrate = 9600
        self.timeout = 0.5
        self.registrationCode = [8, 0, 1, 9]
        self.internalTemperature = 0
        self.referenceTemperature = 0
        self.externalTemperature = 0
    
    def createEvents(self):
        self.on = Event()
        self.working = Event()
        self.heating = Event()
        self.cooling = Event()
        self.timer = Event()
        self.sending = Event()
        
    def startServices(self):
        self.turnOn()
        
        thread_routine = Thread(target=self.routine, args=())
        thread_routine.start()
        
    def turnOn(self):
        self.sending.set()
        command = b'\x01\x23\xd3'
        
        self.uart.send(command, self.registrationCode, b'\x01')
        data = self.uart.receive()
        print(data)
        
        if data is not None:
            self.stop()
            self.on.set()
        
        self.sending.clear()
        
    def turnOff(self):
        self.sending.set()
        command = b'\x01\x23\xd3'

        self.uart.send(command, self.registrationCode, b'\x00')
        data = self.uart.receive()

        if data is not None:
            self.stop()
            self.on.clear()

        self.sending.clear()
        
    def start(self):
        self.sending.set()
        command = b'\x01\x23\xd5'
        
        self.uart.send(command, self.registrationCode, b'\x01')
        data = self.uart.receive()
        
        if data is not None:
            self.working.set()
        
        self.sending.clear()
        
    def stop(self):
        self.sending.set()
        command = b'\x01\x23\xd5'
        
        self.uart.send(command, self.registrationCode, b'\x00')
        data = self.uart.receive()
        
        if data is not None:
            self.working.clear()
            
        self.sending.clear()
        
    def changeMode(self):
        self.sending.set()
        command = b'\x01\x23\xd4'
        
        self.uart.send(command, self.registrationCode, b'\x00')
        data = self.uart.receive()
        
        if data is not None:
            self.working.clear()
            
        self.sending.clear()
        
    def askReferenceTemperature(self):
        command = b'\x01\x23\xc2'
        
        self.uart.send(command, self.registrationCode, b'')
        dados = self.uart.receive()

        if dados is not None:
            self.handleReferenceTemperature(dados)
            
    def handleReferenceTemperature(self, bytes):
        temp = struct.unpack('f', bytes)[0]
        print('temperatura ref', temp)
        
        if temp > 0 and temp < 100:
            self.referenceTemperature = temp
        
        self.setOven()
        
    def sendExternalTemperature(self):
        self.sending.set()
        command = b'\x01\x23\xd1'
        
        temp = struct.pack('<f', round(5.555, 2))

        self.uart.send(command, self.registrationCode, temp)
                
        self.sending.clear()
        
    def routine(self):
        while True:
            self.askInput()
            time.sleep(0.5)
            self.askInput()
            time.sleep(0.5)
            self.askReferenceTemperature()
            self.askInternalTemperature()
            self.askExternalTemperature()
            
    def askInput(self):
        command = b'\x01\x23\xc3'
        
        self.uart.send(command, self.registrationCode, b'')
        data = self.uart.receive()
        
        if data is not None:
            self.handleButton(data)
            
    def askExternalTemperature(self):
        temp = self.i2c.getExternalTemperature()
        self.handleExternalTemperature(temp)
        
    def handleExternalTemperature(self, temperature):
        self.externalTemperature = temperature
        print('temp externa: ', temperature)
        self.sendExternalTemperature()
        
    def askInternalTemperature(self):
        command = b'\x01\x23\xc1'

        self.uart.send(command, self.registrationCode, b'')
        dados = self.uart.receive()

        if dados is not None:
            self.handleInternalTemperature(dados)
            
    def handleInternalTemperature(self, bytes):
        temp = struct.unpack('f', bytes)[0]
        print('temperatura int', self.internalTemperature)
        
        if temp > 0 and temp < 100:
            self.internalTemperature = temp
            
        self.setOven()
        
    def setOven(self):
        if self.on.is_set():
            if self.working.is_set():
                pid = self.pid.pid_control(self.referenceTemperature, self.internalTemperature)
                
                print('pid f', pid)
                
                self.sendControlSignal(pid)
                
                if math.isclose(self.internalTemperature, self.referenceTemperature, rel_tol=1e-2):
                    self.heating.clear()
                    self.cooling.clear()
                elif self.internalTemperature < self.referenceTemperature:
                    self.heating.set()
                    self.cooling.clear()
                elif self.internalTemperature > self.referenceTemperature:
                    self.heating.clear()
                    self.cooling.set()
                    
                if pid > 0: 
                    self.control.warm(pid)
                    self.control.cool(0)
                else:
                    pid *= -1
                    self.control.warm(0)
                    
                    if pid < 40.0:
                        self.control.cool(40.0)
                    else:
                        self.control.cool(pid)
            else:
                pid = self.pid.pid_control(27.0, self.internalTemperature)
                print('pid r', pid)
                
                if pid < 0:
                    self.sendControlSignal(pid)
                    pid *= -1
                    self.control.cool(pid)
                    self.cooling.set()
                else:
                    self.cooling.clear()
                    
                self.control.warm(0)
                self.heating.clear()
            
        else:
            self.control.warm(0)
            self.control.cool(0)
            self.working.clear()
            self.heating.clear()
            self.cooling.clear()
    
    def sendControlSignal(self, pid):
        self.sending.set()
        command = b'\x01\x23\xd1'
        value = round(pid).to_bytes(4, 'little', signed = True)

        self.uart.send(command, self.registrationCode, value)
        
        self.sending.clear()
        
    def handleButton(self, bytes):        
        button = format(bytes[0], '02x')
        
        if button != '00':
            print('botao', button)
            
        if button == 'a1':
            self.turnOn()
        elif button == 'a2':
           self.turnOff()
        elif button == 'a3':
            self.start()
        elif button == 'a4':
            self.stop()
        elif button == 'a5':
            self.changeMode()
        
ReflowOven()