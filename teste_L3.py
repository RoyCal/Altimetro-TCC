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

    print("\nEscolha o pacote:")
    print("1 - Padrão")
    print("2 - Parar")
    print("3 - Infos")
    print("4 - Mede BMP")
    print("5 - Grava Status")
    print("6 - Manual")

    opcao = input("Opção: ").strip().lower()

    # Limpa buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    pacotes = {
        "1": bytes([
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
        "2": bytes([
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
        "3": bytes([
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
        "4": bytes([
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
        "5": bytes([
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
        ])
    }

    if opcao == "6":
        entrada = input("Digite 12 bytes em hexadecimal (ex.: 01 FB 01 37 FF FF FF FF FF FF FF 45) ou pressione ENTER para usar o padrão: ").strip()
        if entrada:
            partes = entrada.replace(",", " ").split()
            if len(partes) != 12:
                print("Erro: informe exatamente 12 bytes.")
                continue
            pacote_tx = bytes(int(p, 16) & 0xFF for p in partes)
        else:
            print("Nenhum byte informado. Usando o pacote padrão.")
            pacote_tx = pacotes["1"]
    else:
        pacote_tx = pacotes.get(opcao, pacotes["1"])

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