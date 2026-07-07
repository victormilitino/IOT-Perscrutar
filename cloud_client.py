import requests
CLOUD_URL = 'https://script.google.com/macros/s/SEU_ID_AQUI/exec'
TIMEOUT_SEGUNDOS = 15

def consultar_tag_na_nuvem(tag: str) -> dict:
    try:
        resposta = requests.get(CLOUD_URL, params={'uid': tag.strip().upper()}, timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
        dados = resposta.json()
        return {'liberado': bool(dados.get('liberado', False)), 'nome': dados.get('nome')}
    except requests.exceptions.RequestException as e:
        print(f'[NUVEM - ERRO] Falha ao consultar validação de tag: {e}')
        return {'liberado': False, 'nome': None}
    except ValueError:
        print('[NUVEM - ERRO] Resposta da nuvem não é um JSON válido.')
        return {'liberado': False, 'nome': None}