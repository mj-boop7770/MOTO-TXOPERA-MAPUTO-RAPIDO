from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timedelta, timezone
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
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        # AJOUT DE DELETE ICI
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # 1. ENREGISTREMENT OU MISE À JOUR DU CHAUFFEUR
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            dados = json.loads(body.decode('utf-8'))

            telephone = dados.get("telephone")
            if not telephone:
                raise ValueError("O número de telefone é obrigatório.")

            novo_motorista = {
                "tipo": dados.get("tipo"),
                "nom": dados.get("nom"),
                "telephone": telephone,
                "plaque": dados.get("plaque"),
                "latitude": float(dados.get("latitude", 0)),
                "longitude": float(dados.get("longitude", 0)),
                "status": "disponivel",
                "registrado_em": firestore.SERVER_TIMESTAMP  # Heure du serveur
            }

            db = firestore.client()
            db.collection("motoristas").document(str(telephone)).set(novo_motorista, merge=True)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            resposta = {"status": "sucesso", "message": "Motorista gravado com sucesso!"}
            self.wfile.write(json.dumps(resposta).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "erro", "message": str(e)}).encode('utf-8'))

    # 2. LECTURE ET FILTRE AUTOMATIQUE (Moins de 2 heures)
    def do_GET(self):
        try:
            db = firestore.client()
            limite_temps = datetime.now(timezone.utc) - timedelta(hours=2)
            
            docs = db.collection("motoristas")\
                     .where("status", "==", "disponivel")\
                     .where("registrado_em", ">=", limite_temps)\
                     .stream()
            
            lista_motoristas = []
            for doc in docs:
                m = doc.to_dict()
                lista_motoristas.append({
                    "id_doc": doc.id,  # TRÈS IMPORTANT : On envoie l'ID pour que le tableau de bord puisse le supprimer
                    "tipo": m.get("tipo"),
                    "nom": m.get("nom"),
                    "telephone": m.get("telephone"),
                    "plaque": m.get("plaque"),
                    "latitude": m.get("latitude"),
                    "longitude": m.get("longitude")
                })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(lista_motoristas).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))

    # 3. SUPPRESSION ACTIVED PAR LE TABLEAU DE BORD (DELETE)
    def do_DELETE(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            dados = json.loads(body.decode('utf-8'))
            id_doc = dados.get("id_doc")

            if not id_doc:
                raise ValueError("ID do documento em falta.")

            db = firestore.client()
            # On supprime le document directement sur Firebase
            db.collection("motoristas").document(str(id_doc)).delete()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps({"status": "deletado", "message": "Motorista removido."}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "erro", "message": str(e)}).encode('utf-8'))
        
