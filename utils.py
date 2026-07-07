import cv2
import os
import shutil

def draw_label(frame, text, x, y, w, h):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

def carregar_cascade(nome_arquivo):
    caminho_original = os.path.join(cv2.data.haarcascades, nome_arquivo)
    pasta_segura = os.path.join(os.environ.get('SystemDrive', 'C:') + os.sep, 'cv_cascades')
    os.makedirs(pasta_segura, exist_ok=True)
    caminho_seguro = os.path.join(pasta_segura, nome_arquivo)
    if not os.path.exists(caminho_seguro):
        shutil.copyfile(caminho_original, caminho_seguro)
    classificador = cv2.CascadeClassifier(caminho_seguro)
    if classificador.empty():
        raise RuntimeError(f"[ERRO] Não foi possível carregar o classificador '{nome_arquivo}'. Verifique se o arquivo existe em: {caminho_original}")
    return classificador
JANELA_FILTRO_OLHOS = 5

def atualizar_liveness(info, olhos_detectados, tempo_atual):
    historico = info.setdefault('historico_olhos', [])
    historico.append(olhos_detectados)
    if len(historico) > JANELA_FILTRO_OLHOS:
        historico.pop(0)
    if len(historico) < JANELA_FILTRO_OLHOS:
        return
    estado_filtrado = historico.count(True) > historico.count(False)
    estado_anterior = info.get('olhos_estado_filtrado')
    if estado_anterior is True and estado_filtrado is False:
        info['ultimo_olhos_change_time'] = tempo_atual
    elif estado_anterior is False and estado_filtrado is True:
        duracao_fechado = tempo_atual - info['ultimo_olhos_change_time']
        if 0.05 < duracao_fechado < 0.6:
            info['liveness_confirmada'] = True
            info.setdefault('modalidades_confirmadas', set()).add('piscada')
    info['olhos_estado_filtrado'] = estado_filtrado
MIN_AMOSTRAS_MOVIMENTO = 15
CONFIRMACOES_CONSECUTIVAS_NECESSARIAS = 4
RAZAO_MOVIMENTO_MINIMA = 0.004
RAZAO_MOVIMENTO_MAXIMA = 0.09

def atualizar_liveness_movimento(info, x, y, w, h, tempo_atual):
    centro_x = x + w / 2
    centro_y = y + h / 2
    historico = info.setdefault('historico_posicao', [])
    historico.append((centro_x, centro_y, w))
    if len(historico) < MIN_AMOSTRAS_MOVIMENTO:
        return
    largura_media = sum((a[2] for a in historico)) / len(historico)
    historico_avaliado = list(historico)
    historico.clear()
    if largura_media <= 0:
        return
    xs = [a[0] / largura_media for a in historico_avaliado]
    ys = [a[1] / largura_media for a in historico_avaliado]
    desvio_x = _desvio_padrao(xs)
    desvio_y = _desvio_padrao(ys)
    movimento_natural = RAZAO_MOVIMENTO_MINIMA < desvio_x < RAZAO_MOVIMENTO_MAXIMA or RAZAO_MOVIMENTO_MINIMA < desvio_y < RAZAO_MOVIMENTO_MAXIMA
    if movimento_natural:
        info['movimento_confirmacoes_seguidas'] = info.get('movimento_confirmacoes_seguidas', 0) + 1
    else:
        info['movimento_confirmacoes_seguidas'] = 0
    if info['movimento_confirmacoes_seguidas'] >= CONFIRMACOES_CONSECUTIVAS_NECESSARIAS:
        info['liveness_confirmada'] = True
        info.setdefault('modalidades_confirmadas', set()).add('movimento')

def _desvio_padrao(valores):
    n = len(valores)
    if n < 2:
        return 0.0
    media = sum(valores) / n
    variancia = sum(((v - media) ** 2 for v in valores)) / n
    return variancia ** 0.5