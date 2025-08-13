# webhook_server.py
import json
import hmac
import hashlib
import requests
import time
from flask import Flask, request, abort
import config
import mercado_livre_api

app = Flask(__name__)

# Arquivo para rastrear perguntas já respondidas
ANSWERED_QUESTIONS_FILE = 'answered_questions.txt'

def load_processed_ids(filename):
    """Carrega os IDs de um arquivo."""
    try:
        with open(filename, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_processed_id(filename, item_id):
    """Salva um ID no arquivo de processados."""
    with open(filename, 'a') as f:
        f.write(str(item_id) + '\n')

def verify_signature(payload_body, signature_header):
    """Verifica a assinatura HMAC para garantir que a requisição veio do Chatwoot."""
    # Função mantida para futura reativação, mas não será chamada na configuração abaixo.
    if not signature_header or not payload_body:
        return False
    secret = config.CHATWOOT_WEBHOOK_SECRET.encode('utf-8')
    signature = signature_header.replace('sha256=', '')
    digest = hmac.new(secret, msg=payload_body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)

@app.route('/webhook', methods=['POST'])
def chatwoot_webhook():
    # --- BLOCO DE VERIFICAÇÃO TEMPORARIAMENTE DESABILITADO ---
    # signature = request.headers.get('X-Chatwoot-Hmac-Sha256')
    # if not verify_signature(request.data, signature):
    #     print("AVISO DE SEGURANÇA: A VERIFICAÇÃO DE ASSINATURA HMAC ESTÁ DESABILITADA.")
    #     # abort(401) # Não abortar
    # --- FIM DO BLOCO DESABILITADO ---

    payload = request.json
    
    if payload.get('event') == 'message_created' and payload.get('message_type') == 'outgoing':
        print("Recebida resposta de um agente no Chatwoot...")
        content = payload.get('content')
        attachments = payload.get('attachments', [])
        custom_attributes = payload.get('conversation', {}).get('custom_attributes', {})
        
        # --- Lógica para Respostas do Chat Pós-Venda (permite múltiplas mensagens) ---
        if 'meli_pack_id' in custom_attributes:
            pack_id = custom_attributes['meli_pack_id']
            if attachments:
                for attachment in attachments:
                    try:
                        file_url = attachment.get('data_url')
                        if not file_url: continue
                        print(f"Processando anexo para enviar ao MELI: {attachment.get('filename', 'anexo')}")
                        file_response = requests.get(file_url, timeout=30)
                        file_response.raise_for_status()
                        mercado_livre_api.send_post_sale_attachment(
                            pack_id, file_response.content, attachment.get('filename', 'anexo')
                        )
                    except Exception as e:
                        print(f"ERRO ao enviar anexo para o pack {pack_id}: {e}")
            if content and content.strip():
                try:
                    mercado_livre_api.send_post_sale_message(pack_id, content)
                except Exception as e:
                    print(f"ERRO ao enviar texto para o pack {pack_id}: {e}")

        # --- Lógica para Respostas de Perguntas de Anúncio (permite apenas UMA resposta) ---
        elif 'meli_question_id' in custom_attributes and content and content.strip():
            question_id = custom_attributes['meli_question_id']
            
            # --- NOVA VERIFICAÇÃO ---
            answered_ids = load_processed_ids(ANSWERED_QUESTIONS_FILE)
            if str(question_id) in answered_ids:
                print(f"AVISO: A pergunta {question_id} já foi respondida. Ignorando nova mensagem.")
                return {'status': 'already_answered'}, 200
            # --- FIM DA NOVA VERIFICAÇÃO ---

            print(f"Enviando resposta para a pergunta do MELI ID: {question_id}")
            try:
                mercado_livre_api.answer_question(question_id, content)
                # Se a resposta foi bem-sucedida, salva o ID para não responder de novo
                save_processed_id(ANSWERED_QUESTIONS_FILE, question_id)
            except Exception as e:
                print(f"ERRO ao responder pergunta {question_id}: {e}")
                
    return {'status': 'success'}, 200

if __name__ == '__main__':
    app.run(port=5000, debug=False)
