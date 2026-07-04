from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée de Firebase via ta variable d'environnement globale
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
            # Récupération sécurisée du contenu JSON envoyé
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
            # ACTION A : SUPPRESSION DEPUIS LE PANNEAU CEO (❌)
            # ----------------------------------------------------
            if data.get("action") == "delete":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"erreur": "ID do documento em falta"}).encode('utf-8'))
                    return
                
                # Suppression définitive dans la collection Firestore
                db.collection("motoristas").document(str(id_doc)).delete()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                # En-têtes anti-cache pour forcer Vercel à détruire la donnée immédiatement
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                
                self.wfile.write(json.dumps({"status": "deletado", "message": "Condutor removido"}).encode('utf-8'))
                return

            # ----------------------------------------------------
            # ACTION B : ENREGISTREMENT DEPUIS LE FORMULAIRE CHAUFFEUR
            # ----------------------------------------------------
            telephone = data.get("telephone")
            if not telephone:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"erreur": "Numero de telefone obrigatorio"}).encode('utf-8'))
                return

            # Préparation de l'objet avec inclusion du statut "disponivel" exigé par ton do_GET
            moto_data = {
                "tipo": data.get("tipo", "moto"),
                "nom": data.get("nom", "Anonimo"),
                "telephone": str(telephone),
                "plaque": data.get("plaque", "Sem Placa"),
                "latitude": float(data.get("latitude")),
                "longitude": float(data.get("longitude")),
                "status": "disponivel"
            }

            # Enregistrement unique (le numéro écrase l'ancienne position)
            db.collection("motoristas").document(str(telephone)).set(moto_data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            self.wfile.write(json.dumps({"status": "sucesso", "message": "Posicao gravada"}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
            
