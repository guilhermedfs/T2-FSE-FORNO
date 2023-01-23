from serial import Serial
import time

from utils.crc16 import calculateCRC

class UART:
    connected = False
    
    def __init__(self, port, baudrate, timeout = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
    def connect(self):
        self.serial = Serial(self.port, self.baudrate, timeout = self.timeout)
        
        if self.serial.isOpen():
            self.connected = True
            print('Porta aberta e conexão realizada.\n')
        else:
            self.connected = False
            print('Porta fechada e conexão não realizada.\n')
    
    def disconnect(self):
        self.serial.close()
        self.connected = False
        
    def send(self, command, registrationCode, value):
        if self.connected:
            # Get message from the message formatter 
            message = self.messageFormatter(command, registrationCode, value)
            
            # Send command with CRC though serial port
            self.serial.write(message)
        else:
            self.connect()
        
    def receive(self):
        if self.connected:
            time.sleep(0.2)
            # Reads the buffer from the serial device
            bufferMessage = self.serial.read(9)
            bufferSize = len(bufferMessage)
            
            if bufferSize == 9:
                data = bufferMessage[3:7]
                receivedCRC16 = bufferMessage[7:9]
                calculatedCRC16 = calculateCRC(bufferMessage[0:7]).to_bytes(2, 'little')
                
                if receivedCRC16 == calculatedCRC16:
                    return data
                else:
                    print('Mensagem recebida: {}'.format(bufferMessage))
                    print('CRC16 Inválido')
                    
                    return None
            else:
                print('Mensagem recebida: {}'.format(bufferMessage))
                print('Mensagem no formato incorreto.')
                
                return None
        else:
            self.connect()
            
            return None
            
    
    def messageFormatter(self, command, registrationCode, value):
        initialMessage = command + bytes(registrationCode) + value
        CRCCode = calculateCRC(initialMessage).to_bytes(2, 'little')
        message = initialMessage + CRCCode
        
        return message