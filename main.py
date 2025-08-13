# main.py
import time
import schedule
import requests
import os # <-- Importado para manipulação de arquivos
import config
import chatwoot_api
import mercado_livre_api

PROCESSED_QUESTIONS_FILE = 'processed_questions.txt'
PROCESSED_MESSAGES_FILE = 'processed_messages.txt'
ANSWERED_QUESTIONS_FILE = 'answered_questions.txt' # Adicionado para garantir a limpeza completa

# --- NOVO BLOCO DE CÓDIGO PARA LIMPEZA ---
def clear_state_files():
    """
    Deleta os arquivos de estado para forçar uma reinicialização completa.
    Esta função deve ser usada apenas para recuperação.
    """
    print("INICIANDO LIMPEZA DE ESTADO...")
    files_to_delete = [
        PROCESSED_QUESTIONS_FILE,
        PROCESSED_MESSAGES_FILE,
        ANSWERED_QUESTIONS_FILE,
        'meli_tokens.db' # Deleta o banco de dados de tokens para forçar a releitura do .env
    ]
    for file in files_to_delete:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"Arquivo de estado '{file}' removido com sucesso.")
        except Exception as e:
            print(f"Erro ao remover o arquivo '{file}': {e}")
    print("LIMPEZA DE ESTADO CONCLUÍDA.")
# --- FIM DO NOVO BLOCO ---

def load_processed_ids(filename):
    """Carrega os IDs de um arquivo para evitar reprocessamento."""
    try:
        with open(filename, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_processed_id(filename, item_id):
    """Salva um ID no arquivo de processados."""
    with open(filename, 'a') as f:
        f.write(str(item_id) + '\n')

def process_questions():
    """Busca perguntas não respondidas e as cria como conversas no Chatwoot."""
    print(f"[{time.ctime()}] Iniciando verificação de perguntas...")
    processed_ids = load_processed_ids(PROCESSED_QUESTIONS_FILE)
    try:
        questions = mercado_livre_api.get_unanswered_questions()
        print(f"Encontradas {len(questions)} perguntas não respondidas.") # Log adicional
    except Exception as e:
        print(f"ERRO ao buscar perguntas no MELI: {e}")
        return

    for q in questions:
        question_id = q['id']
        print(f"Processando pergunta ID: {question_id}...") # Log adicional
        if str(question_id) in processed_ids:
            print(f"Pergunta {question_id} já processada. Ignorando.") # Log adicional
            continue

        print(f"Nova pergunta encontrada: ID {question_id}")
        user_id = q['from']['id']
        try:
            contact_info = chatwoot_api.find_or_create_contact(identifier=user_id, name=f"Cliente MELI (ID: {user_id})")
            item_response = requests.get(
                f"https://api.mercadolibre.com/items/{q['item_id']}",
                headers=mercado_livre_api.get_auth_header()
            )
            item_response.raise_for_status()
            item_info = item_response.json()
            item_title = item_info.get('title', 'Produto não encontrado')
            message_body = f"**Produto:** {item_title}\n**Link:** {item_info.get('permalink', 'N/A')}\n\n**Pergunta:**\n_{q['text']}_"
            meli_attributes = {"meli_question_id": str(question_id)}
            
            chatwoot_api.create_conversation(
                inbox_id=config.CHATWOOT_QUESTIONS_INBOX_ID,
                contact_id=contact_info['id'],
                message_body=message_body,
                custom_attributes=meli_attributes
            )
            save_processed_id(PROCESSED_QUESTIONS_FILE, question_id)
        except Exception as e:
            print(f"Falha ao processar pergunta {question_id}: {e}")
    print(f"[{time.ctime()}] Verificação de perguntas concluída.")

# A função process_messages continua a mesma da versão anterior

def process_messages():
    """Busca mensagens não lidas e as adiciona a conversas existentes ou cria novas."""
    print(f"[{time.ctime()}] Iniciando verificação de mensagens pós-venda...")
    processed_msg_ids = load_processed_ids(PROCESSED_MESSAGES_FILE)
    try:
        orders = mercado_livre_api.get_recent_orders()
        print(f"Encontrados {len(orders)} pedidos recentes para verificar.") # Log adicional
    except Exception as e:
        print(f"ERRO ao buscar pedidos no MELI: {e}")
        return

    for order in orders:
        pack_id = order.get('pack_id')
        try:
            messages = mercado_livre_api.get_messages_for_order(pack_id)
        except Exception as e:
            print(f"ERRO ao buscar mensagens do pack {pack_id}: {e}")
            continue
        
        for msg in reversed(messages):
            msg_id = msg['id']
            if str(msg_id) in processed_msg_ids or str(msg['from']['user_id']) == str(config.MELI_USER_ID):
                continue
            
            print(f"Nova mensagem encontrada no pedido com Pack ID {pack_id}")
            buyer = order.get('buyer', {})
            try:
                existing_conversation = chatwoot_api.search_conversation(pack_id)
                message_text, attachments = msg.get('text', ''), msg.get('attachments', [])

                if existing_conversation:
                    print(f"Conversa existente encontrada (ID: {existing_conversation['id']}). Adicionando nova mensagem.")
                    conversation_id = existing_conversation['id']
                    if not attachments:
                        if not message_text.strip(): continue
                        chatwoot_api.add_message_to_conversation(conversation_id, message_text)
                    else:
                        attachment = attachments[0]
                        file_url, filename = attachment.get('url'), attachment.get('filename', 'anexo.jpg')
                        if not file_url: continue
                        print(f"Baixando anexo: {filename}")
                        file_response = requests.get(file_url, timeout=30)
                        file_response.raise_for_status()
                        chatwoot_api.add_message_to_conversation(
                            conversation_id, message_text,
                            file_content=file_response.content, filename=filename
                        )
                else:
                    print(f"Nenhuma conversa existente para o pack {pack_id}. Criando nova.")
                    contact_info = chatwoot_api.find_or_create_contact(identifier=buyer.get('id'), name=f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip(), email=buyer.get('email'))
                    meli_attributes = {"meli_pack_id": str(pack_id)}
                    if not attachments:
                        if not message_text.strip(): continue
                        message_body = f"**Início da conversa sobre a Venda #{order['id']}**\n\n_{message_text}_"
                        chatwoot_api.create_conversation(
                            inbox_id=config.CHATWOOT_MESSAGES_INBOX_ID, contact_id=contact_info['id'],
                            message_body=message_body, custom_attributes=meli_attributes
                        )
                    else:
                        attachment = attachments[0]
                        file_url, filename = attachment.get('url'), attachment.get('filename', 'anexo.jpg')
                        if not file_url: continue
                        print(f"Baixando anexo: {filename}")
                        file_response = requests.get(file_url, timeout=30)
                        file_response.raise_for_status()
                        message_body = f"**Início da conversa sobre a Venda #{order['id']}**\n\n_{message_text}_"
                        chatwoot_api.create_conversation_with_attachment(
                            inbox_id=config.CHATWOOT_MESSAGES_INBOX_ID, contact_id=contact_info['id'],
                            message_body=message_body, custom_attributes=meli_attributes,
                            file_content=file_response.content, filename=filename
                        )
                save_processed_id(PROCESSED_MESSAGES_FILE, msg_id)
            except Exception as e:
                print(f"Falha ao processar mensagem {msg_id}: {e}")
    print(f"[{time.ctime()}] Verificação de mensagens concluída.")


if __name__ == "__main__":
    # Executa a limpeza de estado UMA VEZ ao iniciar o script.
    clear_state_files()

    print(f"[{time.ctime()}] >>> Iniciando serviço de integração Meli-Chatwoot (Poller) V2.1 - MODO RECUPERAÇÃO <<<")
    try:
        # É necessário importar o config novamente após a limpeza do DB para recarregar os tokens
        import importlib
        importlib.reload(config)
        
        process_questions()
        process_messages()
    except Exception as e:
        print(f"ERRO no ciclo inicial: {e}")

    schedule.every(2).minutes.do(process_questions)
    schedule.every(3).minutes.do(process_messages)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

