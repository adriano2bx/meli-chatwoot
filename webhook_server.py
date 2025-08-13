# webhook_server.py
import json
import hmac
import hashlib
import requests
from flask import Flask, request, abort
import config
import mercado_livre_api

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
    if not verify_signature(request.data, request.headers.get('X-Chatwoot-Hmac-Sha256')):
        print("Alerta de Segurança: Assinatura HMAC inválida.")
        abort(401)

    payload = request.json
    
    if payload.get('event') == 'message_created' and payload.get('message_type') == 'outgoing':
        print("Recebida resposta de um agente no Chatwoot...")
        
        content = payload.get('content')
        attachments = payload.get('attachments', [])
        conversation = payload.get('conversation', {})
        custom_attributes = conversation.get('custom_attributes', {})
        
        # --- Lógica para Respostas do Chat Pós-Venda ---
        if 'meli_pack_id' in custom_attributes:
            pack_id = custom_attributes['meli_pack_id']
            
            # 1. Envia os anexos, se houver
            if attachments:
                for attachment in attachments:
                    try:
                        file_url = attachment.get('data_url')
                        if not file_url: continue
                        filename = attachment.get('filename', 'anexo')
                        print(f"Processando anexo para enviar ao MELI: {filename}")
                        
                        file_response = requests.get(file_url, timeout=30)
                        file_response.raise_for_status()

                        mercado_livre_api.send_post_sale_attachment(
                            pack_id, file_response.content, filename
                        )
                    except Exception as e:
                        print(f"ERRO ao enviar anexo para o pack {pack_id}: {e}")

            # 2. Envia a mensagem de texto, se houver
            if content and content.strip():
                try:
                    mercado_livre_api.send_post_sale_message(pack_id, content)
                except Exception as e:
                    print(f"ERRO ao enviar texto para o pack {pack_id}: {e}")

        # --- Lógica para Respostas de Perguntas de Anúncio (só texto) ---
        elif 'meli_question_id' in custom_attributes and content and content.strip():
            question_id = custom_attributes['meli_question_id']
            print(f"Enviando resposta para a pergunta do MELI ID: {question_id}")
            try:
                mercado_livre_api.answer_question(question_id, content)
            except Exception as e:
                print(f"ERRO ao responder pergunta {question_id}: {e}")

    return {'status': 'success'}, 200

if __name__ == '__main__':
    # Em produção, o Gunicorn é iniciado pelo supervisord.conf
    # Esta linha é para facilitar testes locais.
    app.run(port=5000, debug=False)
