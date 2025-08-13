# config.py
import os
from dotenv import load_dotenv
import db_manager

# Carrega o arquivo .env (importante para desenvolvimento local e para popular o DB na 1ª vez)
load_dotenv()

# --- Configurações estáticas do ambiente ---
MELI_APP_ID = os.getenv("MELI_APP_ID")
MELI_SECRET_KEY = os.getenv("MELI_SECRET_KEY")
MELI_USER_ID = os.getenv("MELI_USER_ID")

CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")
CHATWOOT_QUESTIONS_INBOX_ID = os.getenv("CHATWOOT_QUESTIONS_INBOX_ID")
CHATWOOT_MESSAGES_INBOX_ID = os.getenv("CHATWOOT_MESSAGES_INBOX_ID")
CHATWOOT_WEBHOOK_SECRET = os.getenv("CHATWOOT_WEBHOOK_SECRET")

# --- Tokens dinâmicos (lidos do DB) ---
# Inicializa o DB com os tokens do .env, se o DB estiver vazio.
db_manager.initialize_db(
    initial_access_token=os.getenv("MELI_ACCESS_TOKEN"),
    initial_refresh_token=os.getenv("MELI_REFRESH_TOKEN")
)

# Lê os tokens do banco de dados para usar na aplicação
MELI_ACCESS_TOKEN = db_manager.get_setting('MELI_ACCESS_TOKEN')
MELI_REFRESH_TOKEN = db_manager.get_setting('MELI_REFRESH_TOKEN')

def update_meli_tokens(new_access_token, new_refresh_token):
    """Atualiza os tokens no banco de dados e recarrega as variáveis globais."""
    global MELI_ACCESS_TOKEN, MELI_REFRESH_TOKEN
    
    print("Atualizando tokens de acesso no banco de dados...")
    db_manager.update_setting('MELI_ACCESS_TOKEN', new_access_token)
    db_manager.update_setting('MELI_REFRESH_TOKEN', new_refresh_token)
    
    MELI_ACCESS_TOKEN = new_access_token
    MELI_REFRESH_TOKEN = new_refresh_token
    print("Tokens atualizados com sucesso.")
