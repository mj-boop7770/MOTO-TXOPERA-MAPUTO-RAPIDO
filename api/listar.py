from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

# Initialisation sécurisée de Firebase
firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase : {e}")

# Duração máxima de visibilidade de um condutor sem actualização (2 horas)
LIMITE_VISIBILIDADE = timedelta(hours=2)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            modo_admin = query.get("admin", ["0"])[0] == "1"

            db = firestore.client()

            if modo_admin:
                # PAINEL: vê TODOS os condutores, seja qual for o status,
                # e sem o filtro de 2h — para poderes gerir/apagar mesmo os inactivos.
                docs = db.collection("motoristas").stream()
            else:
                # CLIENTE: só os disponíveis agora mesmo.
                docs = db.collection("motoristas").where("status", "==", "disponivel").stream()

            agora = datetime.now(timezone.utc)
            lista_motoristas = []
            for doc in docs:
                m = doc.to_dict()

                if not modo_admin:
                    # Filtre : ignora condutores sem actividade há mais de 2h
                    atualizado_em = m.get("atualizado_em")
                    if atualizado_em is not None:
                        if (agora - atualizado_em) > LIMITE_VISIBILIDADE:
                            continue
                    # Se não houver atualizado_em (registos antigos), mostra na mesma
                    # para não apagar de repente todos os condutores já existentes.

                lista_motoristas.append({
                    "id_doc": doc.id,  # <--- CRUCIAL : On transmet l'ID réel du document Firebase ici !
                    "tipo": m.get("tipo"),
                    "nom": m.get("nom"),
                    "telephone": m.get("telephone"),
                    "plaque": m.get("plaque"),
                    "latitude": m.get("latitude"),
                    "longitude": m.get("longitude"),
                    "status": m.get("status"),
                    "contactos_total": m.get("contactos_total", 0),
                    "contactos_ligar": m.get("contactos_ligar", 0),
                    "contactos_whatsapp": m.get("contactos_whatsapp", 0),
                    "contactos_sms": m.get("contactos_sms", 0)
                })

            # Réponse avec la liste des marqueurs
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # Évite les blocages de sécurité
            
            # --- CONFIGURATION ANTI-CACHE STRICTE POUR VERCEL ---
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            # ----------------------------------------------------
            
            self.end_headers()
            
            self.wfile.write(json.dumps(lista_motoristas).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
