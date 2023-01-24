from oven.reflow_oven import ReflowOven
from utils.pid import PID
from os import system

if __name__ == "__main__":
    while True:
        system('clear')
        print('Selecione uma opção')
        print('\n')
        print('1. Modo Debug')
        print('2. Modo Dashboard')
        print('3. Modo Curva de Temperatura')
        print('4. Inserir valores para constantes de PID')
        print('\n')
        opt = int(input('Selecione a opção desejada: '))
        
        pid = PID()
        
        if opt == 4:
            print('\n')
            kp = float(input('Insira Kp: '))
            ki = float(input('Insira Ki: '))
            kd = float(input('Insira Kd: '))
            pid.Kp = kp
            pid.Ki = ki
            pid.Kd = kd
        elif opt >= 1 and opt <= 3:
            ReflowOven(int(opt), pid)
            break
