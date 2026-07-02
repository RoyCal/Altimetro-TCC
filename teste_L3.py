import serial
import time

# ==========================
# Configuração da porta
# ==========================
PORTA = "COM6"      # Altere para sua porta
BAUDRATE = 9600

ser = serial.Serial(
    port=PORTA,
    baudrate=BAUDRATE,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

print(f"Conectado em {PORTA}")

while True:

    input("\nPressione ENTER para enviar um pacote...")

    # Limpa buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Pacote de 12 bytes
    pacote_tx = bytes([
        1,
        251,
        1,
        55,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        0
    ])

    print("TX:", " ".join(f"{b:02X}" for b in pacote_tx))

    # Envia
    ser.write(pacote_tx)
    ser.flush()

    # Dá tempo para o PIC responder
    time.sleep(0.02)   # 20 ms

    # Espera até receber 12 bytes
    resposta = bytearray()

    inicio = time.time()

    while len(resposta) < 12:

        if ser.in_waiting:
            resposta.extend(ser.read(1))

        if time.time() - inicio > 1:
            break

    if len(resposta) == 12:
        print("RX:", " ".join(f"{b:02X}" for b in resposta))
    else:
        print(f"Timeout! Recebidos {len(resposta)} bytes.")
        if len(resposta):
            print("Parcial:", " ".join(f"{b:02X}" for b in resposta))

ser.close()