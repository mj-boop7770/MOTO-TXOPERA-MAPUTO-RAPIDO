from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée de Firebase
firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase : {e}")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            db = firestore.client()
            # On récupère tous les chauffeurs disponibles
            docs = db.collection("motoristas").where("status", "==", "disponivel").stream()
            
            lista_motoristas = []
            for doc in docs:
                m = doc.to_dict()
                lista_motoristas.append({
                    "tipo": m.get("tipo"),
                    "nom": m.get("nom"),
                    "telephone": m.get("telephone"),
                    "plaque": m.get("plaque"),
                    "latitude": m.get("latitude"),
                    "longitude": m.get("longitude")
                })

            # Réponse avec la liste des marqueurs
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # Évite les blocages de sécurité
            self.end_headers()
            
            self.wfile.write(json.dumps(lista_motoristas).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
            
