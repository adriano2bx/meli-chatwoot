# db_manager.py
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'meli_tokens.db')

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(initial_access_token=None, initial_refresh_token=None):
    """Cria as tabelas do banco de dados se elas não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela para tokens e configurações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    # --- NOVA TABELA PARA GERENCIAR ESTADO ---
    # Guarda IDs de perguntas, mensagens e respostas já processadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_items (
            item_id TEXT PRIMARY KEY
        )
    ''')

    # Popula os tokens iniciais se a tabela estiver vazia
    cursor.execute("SELECT key FROM settings WHERE key IN ('MELI_ACCESS_TOKEN', 'MELI_REFRESH_TOKEN')")
    existing_keys = [row['key'] for row in cursor.fetchall()]
    
    if 'MELI_ACCESS_TOKEN' not in existing_keys and initial_access_token:
        print("Populando o banco de dados com o Access Token inicial.")
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ('MELI_ACCESS_TOKEN', initial_access_token))

    if 'MELI_REFRESH_TOKEN' not in existing_keys and initial_refresh_token:
        print("Populando o banco de dados com o Refresh Token inicial.")
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ('MELI_REFRESH_TOKEN', initial_refresh_token))

    conn.commit()
    conn.close()

def get_setting(key):
    """Busca um valor de configuração na tabela 'settings'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def update_setting(key, value):
    """Atualiza ou insere um valor de configuração na tabela 'settings'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

# --- NOVAS FUNÇÕES DE GERENCIAMENTO DE ESTADO ---
def is_item_processed(item_id):
    """Verifica se um ID de item já foi processado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_id FROM processed_items WHERE item_id = ?", (str(item_id),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_item_as_processed(item_id):
    """Marca um ID de item como processado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # ON CONFLICT IGNORE faz com que, se o ID já existir, nada aconteça.
    cursor.execute("INSERT OR IGNORE INTO processed_items (item_id) VALUES (?)", (str(item_id),))
    conn.commit()
    conn.close()
