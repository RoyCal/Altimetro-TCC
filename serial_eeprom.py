import serial
import time
from math import pow
import matplotlib.pyplot as plt

ALT_FREQ = 24.6
REPETITION_LIMIT = ALT_FREQ * 5

def pressureToAltitude(p_zero, p):
    return 44330 * (1 - pow((p/p_zero), (1/5.255)))

ser = serial.Serial('COM6', 9600, timeout=0.1)

ser.write(b'R')

print("Esperando dados do PIC...")

ultimo_recebimento = time.time()

buffer = bytearray()
pressao = []
altitudes = []
read = True

current_pressure = 0
last_read_pressure = 0
repetition_count = 0
count_repetition = False

while True:
    data = ser.read(1)

    if read:
        ser.write(b'R')
    else:
        ser.write(b'P')

    if data:
        buffer.extend(data)
        ultimo_recebimento = time.time()

        # Sempre que tiver um par de bytes
        while len(buffer) >= 2:
            valor_raw = (buffer[0] << 8) | buffer[1]

            if valor_raw in (0x0000, 0xFFFF) or repetition_count > REPETITION_LIMIT:
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
            
            altitudes.append(altitude := format(pressureToAltitude(pressao[0], valor), ".2f"))

            print(
                f"{buffer[0]:02X} {buffer[1]:02X} "
                f"-> {valor} Pa"
                f" -> {altitude}m"
            )

            del buffer[:2]

    elif time.time() - ultimo_recebimento >= 2:
        break

ser.close()


print("\nFim da transmissão.")
print(f"Total de amostras: {len(altitudes)}")

time_stamps = []
moment = 0
for i in range(0, len(altitudes)):
    time_stamps.append(moment)
    moment += 1 / ALT_FREQ

plt.plot(time_stamps, altitudes)

plt.xlabel("Tempo (s)")
plt.ylabel("Altitude (m)")
plt.title("Altitude x Tempo")

plt.grid(True)
plt.show()