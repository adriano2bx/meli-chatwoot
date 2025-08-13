# webhook_server.py
import json
import hmac
import hashlib
import requests
import time
from flask import Flask, request, abort
import config
import mercado_livre_api
import db_manager # Importa o gerenciador de banco de dados

app = Flask(__name__)

def verify_signature(payload_body, signature_header):
    """Verifica a assinatura HMAC para garantir que a requisição veio do Chatwoot."""
    if not signature_header or not payload_body:
        return False
    secret = config.CHATWOOT_WEBHOOK_SECRET.encode('utf-8')
    signature = signature_header.replace('sha256=', '')
    digest = hmac.new(secret, msg=payload_body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)

@app.route('/webhook', methods=['POST'])
def chatwoot_webhook():
    # --- Bloco de verificação de segurança (desabilitado temporariamente) ---
    # ...

    payload = request.json
    
    if payload.get('event') == 'message_created' and payload.get('message_type') == 'outgoing':
        print("Recebida resposta de um agente no Chatwoot...")
        content = payload.get('content')
        custom_attributes = payload.get('conversation', {}).get('custom_attributes', {})
        
        # --- Lógica para Respostas de Perguntas de Anúncio ---
        if 'meli_question_id' in custom_attributes and content and content.strip():
            question_id = custom_attributes['meli_question_id']
            
            # --- LÓGICA ATUALIZADA: Verifica no DB se a pergunta já foi respondida ---
            # Usamos um prefixo 'answered-' para diferenciar dos IDs de perguntas recebidas
            if db_manager.is_item_processed(f"answered-{question_id}"):
                print(f"AVISO: A pergunta {question_id} já foi respondida. Ignorando nova mensagem.")
                return {'status': 'already_answered'}, 200

            print(f"Enviando resposta para a pergunta do MELI ID: {question_id}")
            try:
                mercado_livre_api.answer_question(question_id, content)
                # --- LÓGICA ATUALIZADA: Marca a pergunta como respondida no DB ---
                db_manager.mark_item_as_processed(f"answered-{question_id}")
            except Exception as e:
                print(f"ERRO ao responder pergunta {question_id}: {e}")
        
        # --- Lógica para Respostas do Chat Pós-Venda (permanece a mesma) ---
        elif 'meli_pack_id' in custom_attributes:
            # ... (código omitido para brevidade, mas permanece o mesmo)
            pass

    return {'status': 'success'}, 200

if __name__ == '__main__':
    app.run(port=5000, debug=False)
