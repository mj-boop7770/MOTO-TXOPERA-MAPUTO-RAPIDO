from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée de Firebase Haulzao-2
firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase Haulzao-2 : {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            dados = json.loads(body.decode('utf-8'))

            # Structure de ta base Haulzao-2
            novo_motorista = {
                "tipo": dados.get("tipo"),
                "nom": dados.get("nom"),
                "telephone": dados.get("telephone"),
                "plaque": dados.get("plaque"),
                "latitude": dados.get("latitude", 0),
                "longitude": dados.get("longitude", 0),
                "status": "disponivel",
                "registrado_em": firestore.SERVER_TIMESTAMP
            }

            db = firestore.client()
            db.collection("motoristas").add(novo_motorista)

            # Réponse de succès au téléphone
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            resposta = {"status": "sucesso", "message": "Motorista gravado com sucesso no Haulzao-2!"}
            self.wfile.write(json.dumps(resposta).encode('utf-8'))

        except Exception as e:
            # En cas de problème, on affiche la vraie erreur Firebase
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "erro", "message": f"Erro Haulzao-2: {str(e)}"}).encode('utf-8'))
            
