import cv2
import time
from database import Database
from face_engine import FaceEngine
from utils import atualizar_liveness, atualizar_liveness_movimento
from cloud_client import consultar_tag_na_nuvem
COMANDO_BUZZER_OK = 'BEEP_OK'
COMANDO_BUZZER_NEGADO = 'BEEP_NEGADO'

class MockSerial:

    def write(self, comando):
        print(f'   >> [BUZZER SIMULADO] {comando}')

    def close(self):
        pass

def tocar_buzzer(ser, comando):
    ser.write(comando)

def main():
    db = Database()
    people = db.load()
    if not people:
        print('[AVISO] Nenhuma pessoa cadastrada em data.json.')
        print('        Rode register_simulado.py antes de testar.')
    fe = FaceEngine()
    fe.train(people)
    ser = MockSerial()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('[ERRO] Não foi possível abrir a câmera.')
        return
    memoria_validacao = {}
    TEMPO_GRACO_SAIDA = 3.0
    print('\n=== TESTE LOCAL (sem hardware) ===')
    print('O = tag correta | I = tag de outra pessoa | U = tag nao cadastrada | Q = sair\n')
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        tempo_atual = time.time()
        results = fe.detect_and_recognize(frame)
        chaves_no_frame_atual = set()
        pessoa_em_foco = None
        for x, y, w, h, person, olhos_detectados in results:
            chave = person.id if person else 'Desconhecido'
            nome_detectado = person.name if person else 'Desconhecido'
            chaves_no_frame_atual.add(chave)
            if person and pessoa_em_foco is None:
                pessoa_em_foco = person
            if chave in memoria_validacao:
                info = memoria_validacao[chave]
                info['ultimo_visto'] = tempo_atual
            else:
                info = {'nome': nome_detectado, 'status': 'AGUARDANDO', 'msg': 'Aguardando Tag', 'ultimo_visto': tempo_atual, 'liveness_confirmada': False, 'olhos_estado_filtrado': None, 'ultimo_olhos_change_time': tempo_atual, 'historico_olhos': []}
                memoria_validacao[chave] = info
            atualizar_liveness(info, olhos_detectados, tempo_atual)
            atualizar_liveness_movimento(info, x, y, w, h, tempo_atual)
            cor = (0, 255, 0) if info['liveness_confirmada'] else (0, 165, 255)
            status_olhos = 'olhos OK' if olhos_detectados else 'sem olhos'
            n_frames = len(info.get('historico_olhos', []))
            modalidades = info.get('modalidades_confirmadas', set())
            if info['liveness_confirmada']:
                liveness_txt = f'VIVO ({'+'.join(sorted(modalidades))})'
            else:
                liveness_txt = f'aguardando piscada ({n_frames}/5) ou movimento...'
            cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 2)
            cv2.putText(frame, f'{nome_detectado} | {status_olhos} | {liveness_txt}', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
        for chave in [c for c, i in memoria_validacao.items() if tempo_atual - i['ultimo_visto'] > TEMPO_GRACO_SAIDA]:
            del memoria_validacao[chave]
        key = cv2.waitKey(1) & 255
        nova_tag = None
        if key == ord('o') and pessoa_em_foco:
            nova_tag = pessoa_em_foco.tag
            print(f'[TECLADO] Simulando TAG CORRETA de {pessoa_em_foco.name}')
        elif key == ord('i'):
            outra = next((p for p in people if not pessoa_em_foco or p.id != pessoa_em_foco.id), None)
            if outra:
                nova_tag = outra.tag
                print(f'[TECLADO] Simulando TAG DE OUTRA PESSOA ({outra.name})')
            else:
                print('[AVISO] Cadastre pelo menos 2 pessoas pra testar esse cenário.')
        elif key == ord('u'):
            nova_tag = 'TAG_NAO_CADASTRADA_999'
            print('[TECLADO] Simulando TAG NAO CADASTRADA')
        elif key == ord('q'):
            break
        if nova_tag:
            resultado_nuvem = consultar_tag_na_nuvem(nova_tag)
            print(f'   [NUVEM] Resposta: {resultado_nuvem}')
            dono_da_tag = None
            if resultado_nuvem['liberado'] and resultado_nuvem['nome']:
                dono_da_tag = next((p for p in people if p.name.strip().lower() == resultado_nuvem['nome'].strip().lower()), None)
                if dono_da_tag is None:
                    print(f"   [AVISO] Nuvem liberou '{resultado_nuvem['nome']}', mas não há cadastro facial local com esse nome.")
            if dono_da_tag:
                if dono_da_tag.id in memoria_validacao:
                    info = memoria_validacao[dono_da_tag.id]
                    if info['liveness_confirmada']:
                        info.update({'status': 'OK', 'msg': 'TAG OK (NUVEM)'})
                        print(f'   [OK] {dono_da_tag.name} liberado pela nuvem!')
                        tocar_buzzer(ser, COMANDO_BUZZER_OK)
                    else:
                        info.update({'status': 'SUSPEITO_FOTO', 'msg': 'SEM PROVA DE VIDA'})
                        print(f'   [SUSPEITO] {dono_da_tag.name} sem piscar -- possivel foto!')
                        tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
                else:
                    for chave in chaves_no_frame_atual:
                        info = memoria_validacao[chave]
                        info.update({'status': 'INCORRETA', 'msg': f'TAG DE {dono_da_tag.name}'})
                        print(f'   [ALERTA] {info['nome']} usou a tag de {dono_da_tag.name}!')
                        tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
            else:
                for chave in chaves_no_frame_atual:
                    info = memoria_validacao[chave]
                    info.update({'status': 'NAO_CADASTRADA', 'msg': 'TAG NAO AUTORIZADA PELA NUVEM'})
                    print(f'   [ALERTA] {info['nome']} usou tag nao autorizada pela nuvem!')
                    tocar_buzzer(ser, COMANDO_BUZZER_NEGADO)
        cv2.imshow('TESTE LOCAL - Perscrutar Acesso (sem hardware)', frame)
    cap.release()
    cv2.destroyAllWindows()
if __name__ == '__main__':
    main()