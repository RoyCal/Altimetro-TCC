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
        self.baud_rate = 19200
        self.altitudes = []
        self.timestamps = []
        self.croppedAltitudes = []
        self.croppedTimestamps = []
        self.pacotes = {
        "receber": bytes([
            1,
            251,
            1,
            55,
            255,
            6,
            255,
            255,
            255,
            255,
            255,
            52
        ]),
        "parar": bytes([
            1,
            251,
            1,
            55,
            255,
            0,
            255,
            255,
            255,
            255,
            255,
            46
        ]),
        "infos": bytes([
            1,
            251,
            1,
            83,
            1,
            255,
            255,
            255,
            255,
            255,
            255,
            75
        ]),
        "mede_bmp": bytes([
            1,
            251,
            1,
            84,
            1,
            255,
            255,
            255,
            255,
            255,
            255,
            76
        ]),
        "libera_voo": bytes([
            1,
            251,
            1,
            51,
            255,
            255,
            255,
            255,
            255,
            255,
            255,
            41
        ]),
        "testa_eeprom": bytes([
            1,
            251,
            1,
            84,
            2,
            255,
            255,
            255,
            255,
            255,
            255,
            77
        ])
    }

    def pressureToAltitude(self, p_zero, p):
        return round(44330 * (1 - pow((p/p_zero), (1/5.255))), 2)
    
    def retrieve_data(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.baud_rate, timeout=0.1)

            ser.write(self.pacotes["parar"])
            ack = ser.read(12)
            while ack[3] != 6:
                ser.write(self.pacotes["parar"])
                ack = ser.read(12)

            ser.write(self.pacotes["receber"])

            print("Esperando dados do altímetro...")

            pressao_base = 0
            self.altitudes = []
            read = True
            self.time_stamps = []
            moment = 0
            period = 1/self.ALT_FREQ

            first_value = True
            trigger_memory_addr = None

            while read:
                data = ser.read(12)

                if len(data) < 12:
                    ser.write(self.pacotes["parar"])
                    ack = ser.read(12)
                    while ack[3] != 6:
                        ser.write(self.pacotes["parar"])
                        ack = ser.read(12)
                    break

                # Verifica erro na transmissão
                if data[3] == 21:
                    ser.write(self.pacotes["receber"])
                    continue

                if first_value:
                    # Os dois primeiros bytes são o endereço
                    trigger_memory_addr = (data[4] << 8) | data[5]

                    # Os quatro últimos bytes são dois valores de pressão
                    raw_p1 = ((data[6] << 8) | data[7])
                    p1 = raw_p1 * 10
                    pressao_base = p1
                    raw_p2 = ((data[8] << 8) | data[9])
                    p2 = raw_p2 * 10

                    self.altitudes.append(altitude1 := self.pressureToAltitude(pressao_base, p1))
                    self.altitudes.append(altitude2 := self.pressureToAltitude(pressao_base, p2))
                    self.time_stamps.append(moment)
                    moment += period
                    self.time_stamps.append(moment)
                    moment += period

                    first_value = False

                    print(f'{hex(raw_p1)} -> {p1} Pa -> {altitude1}m')
                    print(f'{hex(raw_p2)} -> {p2} Pa -> {altitude2}m')

                else:
                    # Três valores de pressão
                    for i in range(4, 10, 2):
                        if data[i] == 0xFF:
                            if data[i+1] == 0xFF:
                                read = False
                                ser.write(self.pacotes["parar"])
                                ack = ser.read(12)
                                while ack[3] != 6:
                                    ser.write(self.pacotes["parar"])
                                    ack = ser.read(12)
                                break
                        raw_pressure = ((data[i] << 8) | data[i + 1])
                        pressure = raw_pressure * 10
                        self.altitudes.append(altitude := self.pressureToAltitude(pressao_base, pressure))
                        self.time_stamps.append(moment)
                        moment += period
                        print(f'{hex(raw_pressure)} -> {pressure} Pa -> {altitude}m')

                # Solicita o próximo pacote
                if read: 
                    ser.write(self.pacotes["receber"])

            ser.close()

            print("Endereço do trigger:", trigger_memory_addr)
            print("Apogeu: ", self.altitudes[-1], "m", sep="")
            self.altitudes.pop()
            self.time_stamps.pop()

            print("\nFim da transmissão.")
            print(f"Total de amostras: {len(self.altitudes)}")
            print()

            trigger_memory_addr //= 2
            self.altitudes = self.altitudes[trigger_memory_addr-1:self.CYCLE_ADDR_LIMIT] + self.altitudes[:trigger_memory_addr-1] + self.altitudes[self.CYCLE_ADDR_LIMIT:]

            # Return data instead of plotting here so the caller can
            # decide how/where to display it (main thread or separate process).
            return self.time_stamps, self.altitudes
        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")
        finally:
            ser.close()

    def get_alt_infos(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.baud_rate, timeout=0.1)
            ser.write(self.pacotes["infos"])

            print("Esperando dados do altímetro...")

            data = ser.read(12) 
            id_alt = data[5]
            id_software = data[6] & 0x0F
            id_hardware = (data[6] >> 4) & 0x0F
            flights_conter = (data[7] << 8) | data[8]
            status = data[9]
            print(f"ID da placa: {id_alt}")
            print(f"Versão -> software: {id_software}, hardware: {id_hardware}")
            print(f"Contagem de voos: {flights_conter}")
            print(f"Status: {status} ({"recupere os dados" if status == 0x00 else "memória livre"})")
            print()

        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")
        
        finally: 
            try:
                ser.close()

            except UnboundLocalError as e:
                print(f"{e}: Por favor, espere a recuperação terminar!")

    def enable_flight(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.baud_rate, timeout=0.1)
            ser.write(self.pacotes["libera_voo"])

            print("Esperando resposta do altímetro...")

            data = ser.read(12) 

            while data[3] != 6:
                ser.write(self.pacotes["libera_voo"])
                data = ser.read(12)

            print("Voo liberado!")
            print()

        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")
        finally:
            try:
                ser.close()
            except UnboundLocalError as e:
                print(f"{e}: Por favor, espere a recuperação terminar!")
    
    def test_bmp(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.baud_rate, timeout=0.2)
            ser.write(self.pacotes["mede_bmp"])

            print("Esperando resposta do altímetro...")

            data = ser.read(12) 

            while data[3] != 86:
                ser.write(self.pacotes["mede_bmp"])
                data = ser.read(12)

            pressure = int.from_bytes(data[5:9], byteorder="big")
            print(f"Valor lido pelo BMP: {pressure} Pa ({hex(pressure)})")
            print()

        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")
        finally:
            try:
                ser.close()
            except UnboundLocalError as e:
                print(f"{e}: Por favor, espere a recuperação terminar!")
    
    def test_eeprom(self):
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.baud_rate, timeout=0.6)
            ser.write(self.pacotes["testa_eeprom"])

            print("Esperando resposta do altímetro...")

            data = ser.read(12) 

            while data[3] != 86:
                ser.write(self.pacotes["testa_eeprom"])
                data = ser.read(12)

            print("Escrevendo 1, 2, 3, 4 na EEPROM...")
            print(f"Valores lidos da EEPROM: {data[5]}, {data[6]}, {data[7]}, {data[8]}")
            print("Valores originais restaurados...")
            print()

        except:
            print(f"Porta {self.SERIAL_PORT} não disponível")
        finally:
            try:
                ser.close()
            except UnboundLocalError as e:
                print(f"{e}: Por favor, espere a recuperação terminar!")

    def crop_graph_end(self, amount):
        amount = int(len(self.altitudes) - amount*self.ALT_FREQ)

        self.croppedAltitudes = self.altitudes[:-amount]
        self.croppedTimestamps = self.time_stamps[:-amount]
    
    def confirm_crop(self):
        self.altitudes = self.croppedAltitudes
        self.time_stamps = self.croppedTimestamps

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
        plt.show()
    except Exception:
        print("Falha ao gerar o gráfico")

if __name__ == "__main__":
    print("serial_eeprom.py")