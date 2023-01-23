class PID:
    Kp = 30.0  # Ganho Proporcional
    Ki = 0.2  # Ganho Integral
    Kd = 400.0  # Ganho Derivativo
    T = 1.0   # Período de Amostragem (ms)

    total_error = 0.0
    previous_error = 0.0

    control_signal_MAX = 100.0
    control_signal_MIN = -100.0
    control_signal = 0.0

    def pid_control(self, reference, exit_measure):
        error = reference - exit_measure
        self.total_error += error # Acumula o error (Termo Integral)

        if self.total_error >= self.control_signal_MAX:
            self.total_error = self.control_signal_MAX
        elif self.total_error <= self.control_signal_MIN:
            self.total_error = self.control_signal_MIN
        
        delta_error = error - self.previous_error # Diferença entre os erros (Termo Derivativo)
        self.control_signal = self.Kp * error + (self.Ki * self.T) * self.total_error + (self.Kd / self.T) * delta_error # PID calcula sinal de controle

        if self.control_signal >= self.control_signal_MAX:
            self.control_signal = self.control_signal_MAX
        elif self.control_signal <= self.control_signal_MIN:
            self.control_signal = self.control_signal_MIN
        
        self.previous_error = error

        return self.control_signal