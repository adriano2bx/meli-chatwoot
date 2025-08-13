# mercado_livre_api.py
import requests
import functools
import config

BASE_URL = "https://api.mercadolibre.com"

def refresh_access_token():
    """Usa o refresh_token para obter um novo access_token."""
    print("Token de acesso expirado. Tentando renovar...")
    url = f"{BASE_URL}/oauth/token"
    payload = {
        'grant_type': 'refresh_token',
        'client_id': config.MELI_APP_ID,
        'client_secret': config.MELI_SECRET_KEY,
        'refresh_token': config.MELI_REFRESH_TOKEN
    }
    headers = {'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=payload, timeout=15)
    response.raise_for_status()
    new_tokens = response.json()
    config.update_meli_tokens(new_tokens['access_token'], new_tokens['refresh_token'])
    return True

def handle_token_refresh(func):
    """Decorador que intercepta erros de autenticação (401) e renova o token."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print(f"Erro 401 na função '{func.__name__}'.")
                refresh_access_token()
                print("Tentando novamente a chamada à API...")
                return func(*args, **kwargs)
            else:
                raise
    return wrapper

def get_auth_header():
    """Retorna o cabeçalho de autorização atualizado."""
    return {"Authorization": f"Bearer {config.MELI_ACCESS_TOKEN}"}

@handle_token_refresh
def get_unanswered_questions():
    """Busca todas as perguntas não respondidas."""
    url = f"{BASE_URL}/my/received_questions/search"
    params = {"status": "UNANSWERED", "sort_fields": "date_created", "sort_order": "asc"}
    response = requests.get(url, headers=get_auth_header(), params=params, timeout=10)
    response.raise_for_status()
    return response.json().get('questions', [])

@handle_token_refresh
def get_recent_orders():
    """Busca pedidos recentes para verificar por novas mensagens."""
    url = f"{BASE_URL}/orders/search"
    params = {"seller": config.MELI_USER_ID, "sort": "date_desc", "limit": 10}
    response = requests.get(url, headers=get_auth_header(), params=params, timeout=10)
    response.raise_for_status()
    return response.json().get('results', [])

@handle_token_refresh
def get_messages_for_order(pack_id):
    """Busca as mensagens de um pacote de pedido específico."""
    if not pack_id: return []
    messages_url = f"{BASE_URL}/messaging/packs/{pack_id}/messages"
    response = requests.get(messages_url, headers=get_auth_header(), params={"limit": 50, "sort": "date_desc"}, timeout=10)
    response.raise_for_status()
    return response.json().get('messages', [])

@handle_token_refresh
def answer_question(question_id, text):
    """Envia uma resposta de texto para uma pergunta específica."""
    url = f"{BASE_URL}/answers"
    payload = {"question_id": question_id, "text": text}
    response = requests.post(url, headers=get_auth_header(), json=payload, timeout=15)
    response.raise_for_status()
    print(f"Resposta para a pergunta {question_id} enviada com sucesso.")
    return response.json()

@handle_token_refresh
def send_post_sale_message(pack_id, text):
    """Envia uma mensagem de TEXTO para uma conversa de pós-venda."""
    url = f"{BASE_URL}/messages/packs/{pack_id}/sellers/{config.MELI_USER_ID}"
    payload = {"text": text}
    response = requests.post(url, headers=get_auth_header(), json=payload, timeout=15)
    response.raise_for_status()
    print(f"Mensagem de texto para o pack {pack_id} enviada com sucesso.")
    return response.json()

@handle_token_refresh
def send_post_sale_attachment(pack_id, file_content, filename):
    """Envia um ANEXO para uma conversa de pós-venda."""
    url = f"{BASE_URL}/messages/attachments?packId={pack_id}"
    files = {'file': (filename, file_content)}
    auth_header_only = {"Authorization": f"Bearer {config.MELI_ACCESS_TOKEN}"}
    response = requests.post(url, headers=auth_header_only, files=files, timeout=45)
    response.raise_for_status()
    print(f"Anexo {filename} para o pack {pack_id} enviado com sucesso.")
    return response.json()
