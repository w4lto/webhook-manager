"""
Example webhook server for testing tunnels
"""
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json

app = Flask(__name__)

# Stores the most recent received webhooks
webhooks_received = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎣 Webhook Receiver</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
        .status { color: #10b981; font-size: 1.2em; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #6b7280; margin-top: 5px; }
        .webhooks {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .webhook-item {
            border-left: 4px solid #667eea;
            background: #f9fafb;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }
        .webhook-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .method {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        .timestamp { color: #6b7280; font-size: 0.9em; }
        pre {
            background: #1f2937;
            color: #10b981;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin-top: 10px;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 20px;
        }
        .btn:hover { background: #5568d3; }
        .empty { text-align: center; color: #6b7280; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎣 Webhook Receiver</h1>
            <p class="status">✅ Server running and ready to receive webhooks!</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-webhooks">{{ total }}</div>
                <div class="stat-label">Total Webhooks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">POST</div>
                <div class="stat-label">Endpoint: /webhook</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">JSON</div>
                <div class="stat-label">Supported Formats</div>
            </div>
        </div>
        
        <div class="webhooks">
            <h2>Recent Webhooks</h2>
            <button class="btn" onclick="location.reload()">🔄 Refresh</button>
            <button class="btn" onclick="clearWebhooks()" style="background: #ef4444;">🗑️ Clear All</button>
            
            <div id="webhooks-list">
                {% if webhooks %}
                    {% for webhook in webhooks %}
                    <div class="webhook-item">
                        <div class="webhook-header">
                            <span class="method">{{ webhook.method }}</span>
                            <span class="timestamp">{{ webhook.timestamp }}</span>
                        </div>
                        <div><strong>Path:</strong> {{ webhook.path }}</div>
                        {% if webhook.json %}
                        <pre>{{ webhook.json | tojson(indent=2) }}</pre>
                        {% elif webhook.body %}
                        <pre>{{ webhook.body }}</pre>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty">
                        <p>📭 No webhooks received yet</p>
                        <p style="margin-top: 10px; font-size: 0.9em;">Send a POST request to /webhook to get started</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <script>
        async function clearWebhooks() {
            if (confirm('Clear all webhooks?')) {
                await fetch('/webhooks/clear', { method: 'POST' });
                location.reload();
            }
        }
        
        // Auto-refresh every 5 seconds
        setTimeout(() => location.reload(), 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def home():
    """Home page"""
    return render_template_string(
        HTML_TEMPLATE,
        webhooks=reversed(webhooks_received[-10:]),  # Last 10 webhooks
        total=len(webhooks_received)
    )


@app.route('/webhook', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def webhook():
    """Main webhook endpoint"""
    
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
    
    # Parse different data types
    if request.is_json:
        webhook_data['json'] = request.get_json()
    elif request.form:
        webhook_data['form'] = dict(request.form)
    elif request.data:
        try:
            webhook_data['body'] = request.data.decode('utf-8')
        except:
            webhook_data['body'] = '<binary data>'
    
    # Store (keep only last 50)
    webhooks_received.append(webhook_data)
    if len(webhooks_received) > 50:
        webhooks_received.pop(0)
    
    # Console log
    print(f"\n{'='*60}")
    print(f"🎣 Webhook received: {request.method} {request.path}")
    print(f"⏰ Timestamp: {webhook_data['timestamp']}")
    if webhook_data.get('json'):
        print(f"📦 JSON Body: {json.dumps(webhook_data['json'], indent=2)}")
    elif webhook_data.get('body'):
        print(f"📦 Body: {webhook_data['body']}")
    print(f"{'='*60}\n")
    
    return jsonify({
        'status': 'received',
        'timestamp': webhook_data['timestamp'],
        'message': 'Webhook processed successfully!'
    }), 200


@app.route('/webhooks', methods=['GET'])
def list_webhooks():
    """List all webhooks"""
    return jsonify({
        'total': len(webhooks_received),
        'webhooks': webhooks_received
    })


@app.route('/webhooks/clear', methods=['POST'])
def clear_webhooks():
    """Clear webhooks"""
    webhooks_received.clear()
    return jsonify({
        'status': 'cleared',
        'message': 'All webhooks cleared'
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'webhooks_received': len(webhooks_received)
    })


def main():
    """Entry point"""
    print("🚀 Starting webhook server...")
    print("📍 Access: http://localhost:5000")
    print("🎣 Webhook endpoint: http://localhost:5000/webhook")
    print("📋 View webhooks: http://localhost:5000/webhooks")
    print("\n💡 Don't forget to expose with: tunnel start webhook 5000")
    print()
    
    app.run(debug=True, port=5000, host='0.0.0.0')


if __name__ == '__main__':
    main()
