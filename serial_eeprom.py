import serial
import time
from math import pow
import matplotlib.pyplot as plt
import multiprocessing

class SerialEEPROM:
    def __init__(self):
        self.ALT_FREQ = 20
        self.TRIGGER_CYCLE_TIME = 5
        self.CYCLE_ADDR_LIMIT = self.ALT_FREQ * self.TRIGGER_CYCLE_TIME
        self.SERIAL_PORT = "COM6"
        self.altitudes = []
        self.timestamps = []

    def pressureToAltitude(self, p_zero, p):
        return 44330 * (1 - pow((p/p_zero), (1/5.255)))
    
    def retrieve_data(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, 9600, timeout=0.1)

            ser.write(b'R')

            print("Esperando dados do PIC...")

            ultimo_recebimento = time.time()

            buffer = bytearray()
            pressao = []
            self.altitudes = []
            read = True

            current_pressure = 0
            last_read_pressure = 0
            repetition_count = 0
            count_repetition = False
            first_value = True
            trigger_memory_addr = 0
            apogeu = 0

            while True:
                data = ser.read(1)

                if read:
                    ser.write(b'R')
                else:
                    ser.write(b'P')
                    break

                if data:
                    buffer.extend(data)
                    ultimo_recebimento = time.time()

                    # Sempre que tiver um par de bytes
                    while len(buffer) >= 2:
                        valor_raw = (buffer[0] << 8) | buffer[1]

                        if first_value:
                            first_value = False
                            del buffer[:2]
                            trigger_memory_addr = valor_raw
                            continue

                        if valor_raw == 0x5253:
                            read = False
                            break
                        
                        valor = valor_raw * 10
                        current_pressure = valor

                        if len(pressao) == 0:
                            pressao.append(valor)

                        if valor != pressao[0]:
                            count_repetition = True

                        if count_repetition:
                            if current_pressure == last_read_pressure:
                                repetition_count += 1
                            else:
                                repetition_count = 0

                        last_read_pressure = current_pressure
                        
                        self.altitudes.append(altitude := float(format(self.pressureToAltitude(pressao[0], valor), ".2f")))

                        print(
                            f"{buffer[0]:02X} {buffer[1]:02X} "
                            f"-> {valor} Pa"
                            f" -> {altitude}m"
                        )

                        del buffer[:2]

                elif time.time() - ultimo_recebimento >= 2:
                    break

            ser.close()

            print("Endereço do trigger:", trigger_memory_addr)
            print("Apogeu: ", self.altitudes[-1], "m", sep="")
            apogeu = self.altitudes.pop()

            print("\nFim da transmissão.")
            print(f"Total de amostras: {len(self.altitudes)}")

            self.time_stamps = []
            moment = 0
            for i in range(0, len(self.altitudes)):
                self.time_stamps.append(moment)
                moment += 1 / self.ALT_FREQ

            trigger_memory_addr //= 2
            self.altitudes = self.altitudes[trigger_memory_addr-1:self.CYCLE_ADDR_LIMIT] + self.altitudes[:trigger_memory_addr-1] + self.altitudes[self.CYCLE_ADDR_LIMIT:]

            # Return data instead of plotting here so the caller can
            # decide how/where to display it (main thread or separate process).
            return self.time_stamps, self.altitudes
        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")

def plot_altitude(time_stamps, altitudes):
    """Module-level plot function so it can be used as a multiprocessing
    target (picklable) on Windows. Runs a Matplotlib GUI in its own
    process main thread."""
    try:
        plt.plot(time_stamps, altitudes)
        plt.xlabel("Tempo (s)")
        plt.ylabel("Altitude (m)")
        plt.title("Altitude x Tempo")
        plt.grid(True)
        print(plt.yticks())
        plt.show()
    except Exception:
        print("Falha ao gerar o gráfico")

if __name__ == "__main__":
    serial_eeprom = SerialEEPROM()
    result = serial_eeprom.retrieve_data()
    if result:
        time_stamps, altitudes = result
        plot_altitude(time_stamps, altitudes)