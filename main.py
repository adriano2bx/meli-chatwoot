# main.py
import time
import schedule
import requests
import config
import chatwoot_api
import mercado_livre_api
import db_manager # Importa o gerenciador de banco de dados

def process_questions():
    """Busca perguntas não respondidas e as cria como conversas no Chatwoot."""
    print(f"[{time.ctime()}] Iniciando verificação de perguntas...")
    try:
        questions = mercado_livre_api.get_unanswered_questions()
    except Exception as e:
        print(f"ERRO ao buscar perguntas no MELI: {e}")
        return

    for q in questions:
        question_id = q['id']
        # --- LÓGICA ATUALIZADA: Verifica no DB se a pergunta já foi processada ---
        if db_manager.is_item_processed(question_id):
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
            # --- LÓGICA ATUALIZADA: Marca a pergunta como processada no DB ---
            db_manager.mark_item_as_processed(question_id)
        except Exception as e:
            print(f"Falha ao processar pergunta {question_id}: {e}")
    print(f"[{time.ctime()}] Verificação de perguntas concluída.")

def process_messages():
    """Busca mensagens não lidas e as adiciona a conversas existentes ou cria novas."""
    print(f"[{time.ctime()}] Iniciando verificação de mensagens pós-venda...")
    try:
        orders = mercado_livre_api.get_recent_orders()
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
            # --- LÓGICA ATUALIZADA: Verifica no DB se a mensagem já foi processada ---
            if db_manager.is_item_processed(msg_id) or str(msg['from']['user_id']) == str(config.MELI_USER_ID):
                continue
            
            print(f"Nova mensagem encontrada no pedido com Pack ID {pack_id}")
            buyer = order.get('buyer', {})
            try:
                existing_conversation = chatwoot_api.search_conversation(pack_id)
                message_text, attachments = msg.get('text', ''), msg.get('attachments', [])

                if existing_conversation:
                    conversation_id = existing_conversation['id']
                    print(f"Conversa existente encontrada (ID: {conversation_id}). Adicionando nova mensagem.")
                    if not attachments:
                        if not message_text.strip(): continue
                        chatwoot_api.add_message_to_conversation(conversation_id, message_text)
                    else:
                        # Lógica de anexo...
                        pass # (código omitido para brevidade, mas permanece o mesmo)
                else:
                    # Lógica para criar nova conversa...
                    pass # (código omitido para brevidade, mas permanece o mesmo)

                # --- LÓGICA ATUALIZADA: Marca a mensagem como processada no DB ---
                db_manager.mark_item_as_processed(msg_id)
            except Exception as e:
                print(f"Falha ao processar mensagem {msg_id}: {e}")
    print(f"[{time.ctime()}] Verificação de mensagens concluída.")

if __name__ == "__main__":
    print(f"[{time.ctime()}] >>> Iniciando serviço de integração Meli-Chatwoot (Poller) V2.2 <<<")
    try:
        process_questions()
        process_messages()
    except Exception as e:
        print(f"ERRO no ciclo inicial: {e}")

    schedule.every(2).minutes.do(process_questions)
    schedule.every(3).minutes.do(process_messages)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
