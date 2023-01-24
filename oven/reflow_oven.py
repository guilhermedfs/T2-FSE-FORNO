import time
import datetime
import struct
import csv

from threading import Event, Thread

from connections.uart import UART
from utils.pid import PID
from connections.control import Control
from connections.i2c import I2C
from utils.logger import Logger
import utils.messages as msg

class ReflowOven:
    def __init__(self, mode, pid = PID()):
        self.mode = mode
        self.pid = pid
        self.initAll()
        
    def initAll(self):
        self.createVariables()
        self.createEvents()
        self.uart = UART(self.port, self.baudrate, self.timeout)
        self.control = Control(self.resistencePort, self.ventPort)
        self.i2c = I2C()
        self.logger = Logger()
        self.startServices()
        
    def putReferenceTemperature(self):
        temp = float(input('Insira a temperatura de referência: '))
        self.sendReferenceSignal(temp)
        
    def curveReflow(self):
        stop = False
        while stop == False:
            file = open('curva_reflow.csv')
            csvReader = csv.reader(file, delimiter=',')
            for row in csvReader:
                if self.time > row[0]:
                    stop = True
                    break
                elif self.time == row[0]:
                    self.sendReferenceSignal(row[1])
            time.sleep(1)
            self.time += 1
        
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
        self.time = 0
        self.curveOn = False
    
    def createEvents(self):
        self.on = Event()
        self.working = Event()
        self.heating = Event()
        self.cooling = Event()
        self.timer = Event()
        self.sending = Event()
        
    def startServices(self):
        self.turnOn()
        
        if self.mode == 3 or self.mode == 1:
            self.start()
            self.changeMode()
            
        if self.mode == 1:
            self.putReferenceTemperature()
        
        thread_routine = Thread(target=self.routine, args=())
        thread_routine.start()
        
        thread_logger = Thread(target=self.saveLog, args=())
        thread_logger.start()
        
        if self.mode == 3:
            thread_curveReflow = Thread(target=self.curveReflow, args=())
            thread_curveReflow.start()
        
        print('Forno foi iniciado!')
        
    def turnOn(self):
        self.sending.set()
        command = msg.TURNON
        
        self.uart.send(command, self.registrationCode, msg.ONE)
        data = self.uart.receive()
                
        if data is not None:
            self.stop()
            self.on.set()
        
        self.sending.clear()
        
    def sendReferenceSignal(self, referenceTemperature):
        self.sending.set()
        command = msg.SEND_REFERENCE_SIGNAL
        
        temp = struct.pack('<f', round(referenceTemperature, 2))
        
        self.uart.send(command, self.registrationCode, temp)
        
        self.sending.clear()
        
    def turnOff(self):
        self.sending.set()
        command = msg.TURNOFF

        self.uart.send(command, self.registrationCode, msg.ZERO)
        data = self.uart.receive()

        if data is not None:
            self.stop()
            self.on.clear()

        self.sending.clear()
        
    def start(self):
        self.sending.set()
        command = msg.START
        
        self.uart.send(command, self.registrationCode, msg.ONE)
        data = self.uart.receive()
        
        if data is not None:
            self.working.set()
        
        self.sending.clear()
        
    def stop(self):
        self.sending.set()
        command = msg.STOP
        
        self.uart.send(command, self.registrationCode, msg.ZERO)
        data = self.uart.receive()
        
        if data is not None:
            self.working.clear()
            
        self.sending.clear()
        
    def changeMode(self):
        self.curveOn ^= True
        self.sending.set()
        command = msg.CHANGE_MODE
        
        self.uart.send(command, self.registrationCode, msg.ONE if self.curveOn else msg.ZERO)
        data = self.uart.receive()
        
        if data is not None:
            self.working.clear()
            
        self.sending.clear()
        
    def askReferenceTemperature(self):
        command = msg.ASK_REFERENCE_TEMPERATURE
        
        self.uart.send(command, self.registrationCode, msg.EMPTY)
        dados = self.uart.receive()

        if dados is not None:
            self.handleReferenceTemperature(dados)
        else:
            print('Temperatura de referência recebida nula.')
            
    def handleReferenceTemperature(self, bytes):
        temp = struct.unpack('f', bytes)[0]
        print('temperatura ref', temp)
        
        if temp > 0 and temp < 100:
            self.referenceTemperature = temp
                
    def sendExternalTemperature(self):
        self.sending.set()
        command = msg.SEND_EXTERNAL_TEMPERATURE
        
        temp = struct.pack('<f', round(self.externalTemperature, 2))

        self.uart.send(command, self.registrationCode, temp)
                
        self.sending.clear()
        
    def routine(self):
        while True:
            if self.mode == 2:
                self.askInput()
                time.sleep(0.5)
                self.askInput()
                time.sleep(0.5)
                self.askReferenceTemperature()
            self.askInternalTemperature()
            self.askExternalTemperature()
            
    def askInput(self):
        command = msg.ASK_INPUT
        
        self.uart.send(command, self.registrationCode, msg.EMPTY)
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
        command = msg.ASK_INTERNAL_TEMPERATURE

        self.uart.send(command, self.registrationCode, msg.EMPTY)
        dados = self.uart.receive()

        if dados is not None:
            self.handleInternalTemperature(dados)
            
    def handleInternalTemperature(self, bytes):
        temp = struct.unpack('f', bytes)[0]
        print('temperatura int', self.internalTemperature)
        
        if temp > 0 and temp < 100:
            self.internalTemperature = temp
            
        self.setOven()
        
    def saveLog(self):
        header = ['Data e hora', 'Temperatura Interna', 'Temperatura Externa', 'Temperatura Definida', 'Valor de Acionamento']
        self.logger.write(header)
        
        while True:
            data = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            row = [data, self.internalTemperature, self.externalTemperature, self.referenceTemperature, self.pid.control_signal]
            self.logger.write(row)
            time.sleep(1)
        
        
    def setOven(self):
        if self.on.is_set():
            if self.working.is_set():
                pid = self.pid.pid_control(self.referenceTemperature, self.internalTemperature)
                
                print('pid f', pid)
                
                self.sendControlSignal(pid)
                                
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
                pid = self.pid.pid_control(self.externalTemperature, self.internalTemperature)
                
                print('pid', pid)
                
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
        command = msg.SEND_CONTROL_SIGNAL
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