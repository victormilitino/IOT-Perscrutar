import cv2
import serial
import time
import tkinter as tk
from database import Database
from face_engine import FaceEngine
from utils import atualizar_liveness, atualizar_liveness_movimento
from cloud_client import consultar_tag_na_nuvem
PORTA_RFID = 'COM5'
BAUD_RATE = 115200
NOME_JANELA = 'Controle de Acesso - Elevador Inteligente'
COMANDO_BUZZER_OK = b'BEEP_OK\n'
COMANDO_BUZZER_NEGADO = b'BEEP_NEGADO\n'

def tocar_buzzer(ser, comando):
    try:
        ser.write(comando)
    except Exception as e:
        print(f'[BUZZER - AVISO] Não foi possível enviar comando sonoro: {e}')

def main():
    print('[SISTEMA] Inicializando banco de dados e motor facial...')
    db = Database()
    people = db.load()
    fe = FaceEngine()
    fe.train(people)
    print(f'[SISTEMA] Conectando ao leitor RFID na porta {PORTA_RFID}...')
    try:
        ser = serial.Serial(PORTA_RFID, BAUD_RATE, timeout=0.01)
        time.sleep(2)
        ser.flushInput()
        print('[RFID] Conectado com sucesso!')
    except Exception as e:
        print(f'[ERRO CRÍTICO] Falha ao abrir a porta {PORTA_RFID}: {e}')
        return
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print('[ERRO CRÍTICO] Não foi possível abrir a câmera.')
        ser.close()
        return
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()
    print(f'[MONITOR] Tela detectada com resolucao: {screen_width}x{screen_height}')
    webcam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    webcam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cv2.namedWindow(NOME_JANELA, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(NOME_JANELA, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    memoria_validacao = {}
    TEMPO_GRACO_SAIDA = 3.0
    TEMPO_GRACO_ENTRADA = 5.0
    logs_sistema = []

    def adicionar_log(mensagem):
        hora_atual = time.strftime('%H:%M:%S')
        texto_log = f'[{hora_atual}] {mensagem}'
        logs_sistema.append(texto_log)
        if len(logs_sistema) > 7:
            logs_sistema.pop(0)
        print(texto_log)
    adicionar_log('Monitoramento do elevador iniciado localmente.')
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        tempo_atual = time.time()
        results = fe.detect_and_recognize(frame)
        frame = cv2.resize(frame, (screen_width, screen_height))
        chaves_no_frame_atual = set()
        for x_webcam, y_webcam, w_webcam, h_webcam, person, olhos_detectados in results:
            chave = person.id if person else 'Desconhecido'
            nome_detectado = person.name if person else 'Desconhecido'
            chaves_no_frame_atual.add(chave)
            if chave in memoria_validacao:
                info = memoria_validacao[chave]
                info['ultimo_visto'] = tempo_atual
            else:
                info = {'nome': nome_detectado, 'status': 'AGUARDANDO', 'msg': 'Aguardando Tag no Elevador', 'tag': None, 'ultimo_visto': tempo_atual, 'tempo_entrada': tempo_atual, 'alerta_entrada_disparado': False, 'liveness_confirmada': False, 'olhos_estado_filtrado': None, 'ultimo_olhos_change_time': tempo_atual, 'historico_olhos': []}
                memoria_validacao[chave] = info
            atualizar_liveness(info, olhos_detectados, tempo_atual)
            atualizar_liveness_movimento(info, x_webcam, y_webcam, w_webcam, h_webcam, tempo_atual)
        for chave, info in memoria_validacao.items():
            if info['status'] == 'AGUARDANDO' and (not info['alerta_entrada_disparado']):
                if tempo_atual - info['tempo_entrada'] > TEMPO_GRACO_ENTRADA:
                    dono_banco = next((p for p in people if p.id == chave), None)
                    if dono_banco is not None:
                        adicionar_log(f'Alerta: {info['nome']} sem sua tag entrou no elevador')
                        tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
                    info['alerta_entrada_disparado'] = True
        pessoas_para_remover = []
        for chave, info in memoria_validacao.items():
            if tempo_atual - info['ultimo_visto'] > TEMPO_GRACO_SAIDA:
                pessoas_para_remover.append(chave)
        for chave in pessoas_para_remover:
            info_saida = memoria_validacao[chave]
            nome_saida = info_saida['nome']
            tag_saida = info_saida.get('tag')
            status_saida = info_saida.get('status')
            dono_banco = next((p for p in people if p.id == chave), None)
            if status_saida == 'AGUARDANDO' and dono_banco is not None:
                adicionar_log(f'Alerta: {nome_saida} sem sua tag saiu do elevador')
                tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
            elif not tag_saida:
                tag_saida = dono_banco.tag if dono_banco else 'SEM TAG'
                adicionar_log(f'{nome_saida} com a tag {tag_saida} saiu do elevador.')
            else:
                adicionar_log(f'{nome_saida} com a tag {tag_saida} saiu do elevador.')
            del memoria_validacao[chave]
        nova_tag = None
        if ser.in_waiting > 0:
            leitura = ser.readline().decode('utf-8').strip()
            if leitura:
                nova_tag = leitura
        if nova_tag:
            resultado_nuvem = consultar_tag_na_nuvem(nova_tag)
            dono_da_tag = None
            if resultado_nuvem['liberado'] and resultado_nuvem['nome']:
                dono_da_tag = next((p for p in people if p.name.strip().lower() == resultado_nuvem['nome'].strip().lower()), None)
            if dono_da_tag:
                if dono_da_tag.id in memoria_validacao:
                    info = memoria_validacao[dono_da_tag.id]
                    if info['liveness_confirmada']:
                        info.update({'status': 'OK', 'msg': f'TAG OK ({nova_tag})', 'tag': nova_tag})
                        adicionar_log(f'{dono_da_tag.name} validou a tag (nuvem) e liberou o andar.')
                        tocar_buzzer(ser, COMANDO_BUZZER_OK)
                    else:
                        info.update({'status': 'SUSPEITO_FOTO', 'msg': 'PISCADA NAO DETECTADA - POSSIVEL FOTO', 'tag': nova_tag})
                        adicionar_log(f'Alerta: tentativa de acesso de {dono_da_tag.name} sem prova de vida (possível foto)')
                        tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
                else:
                    for chave in chaves_no_frame_atual:
                        info = memoria_validacao[chave]
                        if info['status'] != 'OK':
                            info.update({'status': 'INCORRETA', 'msg': f'TAG DE: {dono_da_tag.name.upper()}', 'tag': nova_tag})
                            adicionar_log(f'Alerta: {info['nome']} entrou com a tag de {dono_da_tag.name}')
                            tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
            else:
                for chave in chaves_no_frame_atual:
                    info = memoria_validacao[chave]
                    if info['status'] != 'OK':
                        info.update({'status': 'NAO_CADASTRADA', 'msg': 'TAG NAO AUTORIZADA PELA NUVEM', 'tag': nova_tag})
                        adicionar_log(f'Alerta: {info['nome']} entrou no elevador, tag nao reconhecida')
                        tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
        cv2.rectangle(frame, (0, 0), (screen_width, 50), (15, 15, 15), cv2.FILLED)
        texto_banner = 'ELEVADOR EM OPERACAO: Monitorando acessos simultaneos...'
        cor_banner = (255, 255, 255)
        for chave in chaves_no_frame_atual:
            info = memoria_validacao.get(chave)
            if info and info['status'] in ['INCORRETA', 'NAO_CADASTRADA', 'SUSPEITO_FOTO']:
                texto_banner = f'ALERTA DE SEGURANCA: {info['nome'].upper()} - {info['msg']}'
                cor_banner = (0, 0, 255)
                break
            elif info and info['status'] == 'OK':
                texto_banner = f'PASSAGEIRO AUTORIZADO: {info['nome']}'
                cor_banner = (0, 255, 0)
        cv2.line(frame, (0, 50), (screen_width, 50), cor_banner, 2)
        cv2.putText(frame, texto_banner, (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_banner, 2, cv2.LINE_AA)
        for x_webcam, y_webcam, w_webcam, h_webcam, person, olhos_detectados in results:
            chave = person.id if person else 'Desconhecido'
            nome_rosto = person.name if person else 'Desconhecido'
            info = memoria_validacao.get(chave)
            x = int(x_webcam * (screen_width / webcam_w))
            y = int(y_webcam * (screen_height / webcam_h))
            w = int(w_webcam * (screen_width / webcam_w))
            h = int(h_webcam * (screen_height / webcam_h))
            if info:
                if info['status'] == 'OK':
                    cor_box = (0, 255, 0)
                    texto_box = f'{nome_rosto}: {info['msg']}'
                elif info['status'] in ['INCORRETA', 'NAO_CADASTRADA', 'SUSPEITO_FOTO']:
                    cor_box = (0, 0, 255)
                    texto_box = f'{nome_rosto}: {info['msg']}'
                else:
                    cor_box = (0, 165, 255)
                    texto_box = f'{nome_rosto} (Aguardando Tag)'
            else:
                cor_box = (0, 165, 255)
                texto_box = f'{nome_rosto} (Aguardando Tag)'
            cv2.rectangle(frame, (x, y), (x + w, y + h), cor_box, 2)
            cv2.rectangle(frame, (x, y - 28), (x + w, y), cor_box, cv2.FILLED)
            cv2.putText(frame, texto_box, (x + 5, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (20, screen_height - 210), (550, screen_height - 20), (10, 10, 10), cv2.FILLED)
        cv2.rectangle(frame, (20, screen_height - 210), (550, screen_height - 20), (0, 165, 255), 1)
        cv2.putText(frame, 'HISTORICO DE EVENTOS DO ELEVADOR', (30, screen_height - 185), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA)
        posicao_y_inicial = screen_height - 155
        for log in logs_sistema:
            if 'saiu do elevador' in log and 'Alerta:' not in log:
                cor_linha_log = (255, 150, 0)
            elif 'Alerta:' in log:
                cor_linha_log = (0, 0, 255)
            else:
                cor_linha_log = (220, 220, 220)
            cv2.putText(frame, log, (30, posicao_y_inicial), cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor_linha_log, 1, cv2.LINE_AA)
            posicao_y_inicial += 22
        cv2.imshow(NOME_JANELA, frame)
        if cv2.waitKey(1) & 255 == ord('q'):
            break
    cap.release()
    ser.close()
    cv2.destroyAllWindows()
if __name__ == '__main__':
    main()