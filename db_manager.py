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
    """Cria a tabela de configurações se ela não existir e a popula com os tokens iniciais."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
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
    """Busca um valor de configuração no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def update_setting(key, value):
    """Atualiza ou insere um valor de configuração no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()
