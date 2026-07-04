from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée de Firebase à ta façon (via le JSON complet)
firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase : {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Récupération de la longueur des données reçues
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if not data:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erreur": "Nenhum dado recebido"}).encode('utf-8'))
                return

            db = firestore.client()

            # ----------------------------------------------------
            # ACTION 1 : SUPPRESSION DEPUIS LE PANNEAU CEO (❌)
            # ----------------------------------------------------
            if data.get("action") == "delete":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"erreur": "ID do documento em falta"}).encode('utf-8'))
                    return
                
                # Suppression propre du document dans Firebase
                db.collection("motoristas").document(str(id_doc)).delete()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "deletado", "message": "Condutor removido"}).encode('utf-8'))
                return

            # ----------------------------------------------------
            # ACTION 2 : ENREGISTREMENT DEPUIS LE FORMULAIRE MOTORISTA
            # ----------------------------------------------------
            telephone = data.get("telephone")
            if not telephone:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erreur": "Numero de telefone obrigatorio"}).encode('utf-8'))
                return

            # On prépare les données et on ajoute IMPORTANT l'état disponible exigé par ton GET !
            moto_data = {
                "tipo": data.get("tipo", "moto"),
                "nom": data.get("nom", "Anonimo"),
                "telephone": str(telephone),
                "plaque": data.get("plaque", "Sem Placa"),
                "latitude": float(data.get("latitude")),
                "longitude": float(data.get("longitude")),
                "status": "disponivel"  # Indispensable pour que ton code do_GET l'affiche sur la carte !
            }

            # Enregistrement dans Firebase (avec le numéro de téléphone comme identifiant unique)
            db.collection("motoristas").document(str(telephone)).set(moto_data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "sucesso", "message": "Posicao gravada"}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
