#!/usr/bin/env python3
"""
Exemplo de servidor webhook para testar o tunnel
Execute: python webhook_server.py
Depois: tunnel start webhook 5000
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# Armazena os últimos webhooks recebidos
webhooks_received = []

@app.route('/')
def home():
    return '''
    <h1>🎣 Webhook Receiver</h1>
    <p>Servidor rodando e pronto para receber webhooks!</p>
    <p><a href="/webhooks">Ver webhooks recebidos</a></p>
    <p><a href="/test">Testar webhook</a></p>
    '''

@app.route('/webhook', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def webhook():
    """Endpoint principal para receber webhooks"""
    
    webhook_data = {
        'timestamp': datetime.now().isoformat(),
        'method': request.method,
        'path': request.path,
        'headers': dict(request.headers),
        'query_params': dict(request.args),
        'body': None,
        'json': None,
        'form': None,
    }
    
    # Tenta parsear diferentes tipos de dados
    if request.is_json:
        webhook_data['json'] = request.get_json()
    elif request.form:
        webhook_data['form'] = dict(request.form)
    elif request.data:
        try:
            webhook_data['body'] = request.data.decode('utf-8')
        except:
            webhook_data['body'] = '<binary data>'
    
    # Armazena (mantém apenas os últimos 50)
    webhooks_received.append(webhook_data)
    if len(webhooks_received) > 50:
        webhooks_received.pop(0)
    
    # Log no console
    print(f"\n{'='*60}")
    print(f"🎣 Webhook recebido: {request.method} {request.path}")
    print(f"⏰ Timestamp: {webhook_data['timestamp']}")
    print(f"📋 Headers: {json.dumps(dict(request.headers), indent=2)}")
    if webhook_data.get('json'):
        print(f"📦 JSON Body: {json.dumps(webhook_data['json'], indent=2)}")
    elif webhook_data.get('body'):
        print(f"📦 Body: {webhook_data['body']}")
    print(f"{'='*60}\n")
    
    return jsonify({
        'status': 'received',
        'timestamp': webhook_data['timestamp'],
        'message': 'Webhook processado com sucesso!'
    }), 200

@app.route('/webhooks', methods=['GET'])
def list_webhooks():
    """Lista todos os webhooks recebidos"""
    return jsonify({
        'total': len(webhooks_received),
        'webhooks': webhooks_received
    })

@app.route('/webhooks/clear', methods=['POST'])
def clear_webhooks():
    """Limpa a lista de webhooks"""
    webhooks_received.clear()
    return jsonify({'status': 'cleared', 'message': 'Todos os webhooks foram removidos'})

@app.route('/test', methods=['GET'])
def test():
    """Página de teste para enviar webhooks"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Webhook Tester</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; box-sizing: border-box; }
            button { background: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background: #45a049; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🧪 Webhook Tester</h1>
        
        <form id="webhookForm">
            <div class="form-group">
                <label>Método HTTP:</label>
                <select id="method">
                    <option value="POST">POST</option>
                    <option value="GET">GET</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                    <option value="PATCH">PATCH</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>JSON Body:</label>
                <textarea id="body" rows="10">{
  "event": "test",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "user_id": 123,
    "action": "purchase",
    "amount": 99.99
  }
}</textarea>
            </div>
            
            <button type="submit">Enviar Webhook</button>
        </form>
        
        <h2>Resposta:</h2>
        <pre id="response">Nenhuma resposta ainda...</pre>
        
        <script>
            document.getElementById('webhookForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const method = document.getElementById('method').value;
                const body = document.getElementById('body').value;
                
                try {
                    const response = await fetch('/webhook', {
                        method: method,
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Custom-Header': 'test-value'
                        },
                        body: method !== 'GET' ? body : undefined
                    });
                    
                    const data = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    document.getElementById('response').textContent = 'Erro: ' + error.message;
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'webhooks_received': len(webhooks_received)
    })

if __name__ == '__main__':
    print("🚀 Iniciando servidor webhook...")
    print("📍 Acesse: http://localhost:5000")
    print("🎣 Endpoint webhook: http://localhost:5000/webhook")
    print("📋 Ver webhooks: http://localhost:5000/webhooks")
    print("🧪 Testar: http://localhost:5000/test")
    print("\n💡 Não esqueça de expor com: tunnel start webhook 5000")
    print()
    
    app.run(debug=True, port=5000, host='0.0.0.0')
