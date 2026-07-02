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
    def do_GET(self):
        try:
            db = firestore.client()
            
            # On récupère uniquement les chauffeurs qui ont le statut "disponivel"
            docs = db.collection("motoristas").where("status", "==", "disponivel").stream()
            
            lista_motoristas = []
            for doc in docs:
                data = doc.to_dict()
                # On retire l'horodatage pour éviter les bugs de conversion JSON
                if "registrado_em" in data:
                    del data["registrado_em"]
                lista_motoristas.append(data)
            
            # Réponse au client
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(lista_motoristas).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                    
