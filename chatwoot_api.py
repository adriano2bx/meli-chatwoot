# chatwoot_api.py
import requests
import json
import config

BASE_URL = f"{config.CHATWOOT_URL}/api/v1/accounts/{config.CHATWOOT_ACCOUNT_ID}"
HEADERS = {"api_access_token": config.CHATWOOT_API_TOKEN, "Content-Type": "application/json; charset=utf-8"}
MULTIPART_HEADERS = {"api_access_token": config.CHATWOOT_API_TOKEN}

def find_or_create_contact(identifier, name, email=None):
    """Busca um contato pelo identifier (ID do usuário MELI), se não encontrar, cria um novo."""
    search_url = f"{BASE_URL}/contacts/search"
    response = requests.get(search_url, headers=HEADERS, params={'q': str(identifier)})
    response.raise_for_status()
    data = response.json()
    if data['meta']['count'] > 0:
        return data['payload'][0]
    else:
        create_url = f"{BASE_URL}/contacts"
        payload = {"name": name, "email": email, "avatar_url": https://logodownload.org/wp-content/uploads/2016/08/mercado-livre-logo-0-1.png, "identifier": str(identifier)}
        response = requests.post(create_url, headers=HEADERS, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()['payload']['contact']

def create_conversation_with_attachment(inbox_id, contact_id, message_body, custom_attributes, file_content, filename):
    """Cria uma conversa no Chatwoot já com um anexo usando multipart/form-data."""
    conv_url = f"{BASE_URL}/conversations"
    data = {
        "inbox_id": inbox_id, "contact_id": contact_id, "content": message_body,
        "message_type": "incoming", "status": "open", "custom_attributes": json.dumps(custom_attributes)
    }
    files = {'attachments[]': (filename, file_content)}
    response = requests.post(conv_url, headers=MULTIPART_HEADERS, data=data, files=files, timeout=45)
    if response.status_code == 200:
        print(f"Sucesso: Conversa com anexo criada no inbox {inbox_id}.")
    else:
        print(f"Erro ao criar conversa com anexo: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()

def create_conversation(inbox_id, contact_id, message_body, custom_attributes=None):
    """Cria uma nova conversa (APENAS TEXTO) em uma caixa de entrada específica."""
    conv_url = f"{BASE_URL}/conversations"
    payload = {
        "inbox_id": inbox_id, "contact_id": contact_id,
        "message": {"content": message_body, "message_type": "incoming"}, "status": "open"
    }
    if custom_attributes:
        payload["custom_attributes"] = custom_attributes
    response = requests.post(conv_url, headers=HEADERS, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    if response.status_code == 200:
        print(f"Sucesso: Conversa de texto criada no inbox {inbox_id}.")
    else:
        print(f"Erro ao criar conversa de texto: {response.status_code} - {response.text}")
    response.raise_for_status()
    return response.json()

# --- NOVA FUNÇÃO DA V2.1 ---
def search_conversation(pack_id):
    """Busca por uma conversa existente usando o 'meli_pack_id' como atributo personalizado."""
    filter_url = f"{BASE_URL}/conversations/filter"
    payload = {
        "payload": [
            {
                "attribute_key": "meli_pack_id",
                "attribute_model": "conversation_attribute",
                "filter_operator": "equal_to",
                "values": [str(pack_id)],
                "query_operator": "and"
            }
        ]
    }
    try:
        response = requests.post(filter_url, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        if data['meta']['count'] > 0:
            # Retorna o objeto da primeira conversa encontrada
            return data['payload'][0]
    except Exception as e:
        print(f"Erro ao buscar conversa para o pack {pack_id}: {e}")
    return None

# --- NOVA FUNÇÃO DA V2.1 ---
def add_message_to_conversation(conversation_id, message_body, file_content=None, filename=None):
    """Adiciona uma nova mensagem (texto ou anexo) a uma conversa existente."""
    message_url = f"{BASE_URL}/conversations/{conversation_id}/messages"
    
    if file_content:
        # Requisição Multipart para anexos
        data = {"content": message_body, "message_type": "incoming"}
        files = {'attachments[]': (filename, file_content)}
        response = requests.post(message_url, headers=MULTIPART_HEADERS, data=data, files=files, timeout=45)
    else:
        # Requisição JSON apenas para texto
        payload = {"content": message_body, "message_type": "incoming"}
        response = requests.post(message_url, headers=HEADERS, json=payload)
        
    if response.status_code == 200:
        print(f"Sucesso: Mensagem adicionada à conversa {conversation_id}.")
    else:
        print(f"Erro ao adicionar mensagem à conversa {conversation_id}: {response.status_code} - {response.text}")
        
    response.raise_for_status()
    return response.json()
