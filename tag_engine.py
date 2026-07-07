import serial
import threading
import time

class TagEngine:
    def __init__(self, port="COM5", baud_rate=115200, timeout_seconds=4):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_seconds = timeout_seconds
        self.active_tags = {}

        self.thread = threading.Thread(target=self._listen_serial, daemon=True)
        self.thread.start()

    def _listen_serial(self):
        """ Loop executado em background para capturar as tags do ESP32 """
        while True:
            try:
                with serial.Serial(self.port, self.baud_rate, timeout=0.1) as ser:
                    print(f"[RFID] Conectado com sucesso na porta {self.port}!")
                    while True:
                        if ser.in_waiting > 0:
                            linha = ser.readline().decode('utf-8').strip()
                            if linha and "PRONTO" not in linha:
                                print(f"[RFID] Tag detectada via Hardware: {linha}")
                                self.active_tags[linha] = time.time()
                        time.sleep(0.01)
            except (serial.SerialException, IndexError):
                print(f"[RFID - AVISO] Aguardando liberacao da porta {self.port}...")
                time.sleep(3)

    def _get_valid_tags(self):
        """ Filtra e retorna apenas as tags que foram lidas nos últimos X segundos """
        agora = time.time()
        return [tag for tag, timestamp in self.active_tags.items() if agora - timestamp < self.timeout_seconds]

    def has_tag(self, tag):
        """ Verifica se a tag da pessoa está na lista de tags lidas recentemente """
        return tag in self._get_valid_tags()

    def any_known_tag_owner(self, people):
        """ Verifica se alguma das tags lidas recentemente pertence a alguém no banco de dados """
        tags_validas = self._get_valid_tags()
        for tag in tags_validas:
            for p in people:
                if p.tag == tag:
                    return p
        return None