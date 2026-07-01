from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Lire les données envoyées par le formulaire
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # 2. Convertir les données en dictionnaire Python
        dados_moto = json.loads(post_data.decode('utf-8'))
        
        print(f"Motorista recebido: {dados_moto['nom']}")

        # 3. Répondre à l'interface que tout est validé
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # Pour éviter les blocages de sécurité entre domaines (CORS)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        resposta = {"status": "success", "message": f"Motorista {dados_moto['nom']} gravado com sucesso!"}
        self.wfile.write(json.dumps(resposta).encode('utf-8'))
        return

    def do_OPTIONS(self):
        # Gestion des requêtes de vérification des navigateurs
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
