from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée de Firebase Octopus2
# On récupère la clé cachée dans Vercel
firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        # On charge le texte JSON de la variable d'environnement
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase : {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Lire les données envoyées par le formulaire HTML
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        dados = json.loads(post_data.decode('utf-8'))
        
        try:
            # 2. Connexion à la collection "motoristas" de ton Firestore
            db = firestore.client()
            
            # 3. Préparation des données propres
            novo_motorista = {
                "tipo": dados.get("tipo"),
                "nom": dados.get("nom"),
                "telephone": dados.get("telephone"),
                "plaque": dados.get("plaque"),
                "status": "disponivel",
                "registrado_em": firestore.SERVER_TIMESTAMP
            }
            
            # 4. Enregistrement dans Firestore (La ligne magique !)
            # On utilise le numéro de téléphone comme identifiant unique
            phone_id = dados.get("telephone").strip()
            db.collection("motoristas").document(phone_id).set(novo_motorista)
            
            # 5. Réponse de succès renvoyée au téléphone du chauffeur
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"message": f"Motorista {dados.get('nom')} gravado com sucesso no Firestore!"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            # En cas de problème avec Firebase
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": f"Erro Octopus: Não foi possível salvar no sistema. ({str(e)})"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
