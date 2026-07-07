import os
import cv2
import serial
import time
from database import Database
from models import Person
from utils import carregar_cascade
PORTA_RFID = 'COM5'
BAUD_RATE = 115200
face_cascade = carregar_cascade('haarcascade_frontalface_default.xml')
profile_cascade = carregar_cascade('haarcascade_profileface.xml')

def buscar_rosto_todos_angulos(frame_cinza):
    faces = face_cascade.detectMultiScale(frame_cinza, 1.1, 4)
    if len(faces) > 0:
        return faces
    faces_esq = profile_cascade.detectMultiScale(frame_cinza, 1.1, 4)
    if len(faces_esq) > 0:
        return faces_esq
    frame_espelhado = cv2.flip(frame_cinza, 1)
    faces_dir = profile_cascade.detectMultiScale(frame_espelhado, 1.1, 4)
    if len(faces_dir) > 0:
        largura_imagem = frame_cinza.shape[1]
        faces_corrigidas = []
        for x, y, w, h in faces_dir:
            x_real = largura_imagem - x - w
            faces_corrigidas.append((x_real, y, w, h))
        return faces_corrigidas
    return []

def register_person():
    db = Database()
    name = input('Nome: ')
    print(f'\n[RFID] Conectando ao leitor na porta {PORTA_RFID}...')
    try:
        ser = serial.Serial(PORTA_RFID, BAUD_RATE, timeout=1)
        time.sleep(2)
        ser.flushInput()
        print('[RFID] Aguardando leitura... Aproxime a tag do leitor ESP32.')
        tag = ''
        while not tag:
            if ser.in_waiting > 0:
                leitura = ser.readline().decode('utf-8').strip()
                if leitura:
                    tag = leitura
                    print(f'[RFID] Tag detectada: {tag}\n')
        ser.close()
    except Exception as e:
        print(f'\n[ERRO] Porta serial ocupada ou desconectada: {e}')
        return
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print('Erro ao acessar a câmera')
        return
    print('=== INSTRUÇÕES PARA ULTRA PRECISÃO ===')
    print("Pressione 'c' para iniciar a captura de 30 fotos.")
    print('Mova o rosto devagar: Olhe para os lados (perfil), para cima e para baixo.')
    print("Pressione 'q' to sair...")
    saved = False
    person_dir = f'faces/{name}'
    os.makedirs(person_dir, exist_ok=True)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray_preview = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_detected = buscar_rosto_todos_angulos(gray_preview)
        frame_clone = frame.copy()
        for x, y, w, h in faces_detected:
            cv2.rectangle(frame_clone, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow('Cadastro - Mova o Rosto em Vários Ângulos', frame_clone)
        key = cv2.waitKey(1) & 255
        if key == ord('c'):
            print('\n[SISTEMA] Capturando... Gire o rosto devagar (lados, cima, baixo)!')
            count = 0
            while count < 40:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = buscar_rosto_todos_angulos(gray)
                for x, y, w, h in faces:
                    face_roi = gray[y:y + h, x:x + w]
                    face_roi = cv2.resize(face_roi, (200, 200))
                    image_path = f'{person_dir}/{count}.jpg'
                    cv2.imwrite(image_path, face_roi)
                    count += 1
                    print(f'Capturada foto {count}/40...')
                    time.sleep(0.08)
                cv2.imshow('Cadastro - Mova o Rosto em Vários Ângulos', frame)
                cv2.waitKey(1)
            print(f'[SUCESSO] Dataset completo criado em {person_dir}')
            saved = True
            break
        elif key == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    if not saved:
        print('Cadastro cancelado.')
        return
    person = Person(name=name, image_path=person_dir, tag=tag)
    db.add_person(person)
    print(f"Pessoa '{name}' cadastrada com mapeamento 3D facial completo!")
if __name__ == '__main__':
    register_person()