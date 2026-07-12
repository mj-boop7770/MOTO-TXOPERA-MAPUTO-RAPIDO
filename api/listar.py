from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

firebase_config = os.environ.get("FIREBASE_CONFIG")

if firebase_config and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Erreur d'initialisation Firebase : {e}")

LIMITE_VISIBILIDADE = timedelta(hours=2)

def montar_motorista(doc):
    m = doc.to_dict()

    pedido = m.get("cliente_pedido")
    pedido_limpo = None
    if pedido:
        pedido_limpo = {
            "status": pedido.get("status"),
            "cliente_lat": pedido.get("cliente_lat"),
            "cliente_lng": pedido.get("cliente_lng")
        }

    return {
        "id_doc": doc.id,
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
        "contactos_sms": m.get("contactos_sms", 0),
        "cliente_pedido": pedido_limpo
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            modo_admin = query.get("admin", ["0"])[0] == "1"
            id_doc_unico = query.get("id_doc", [None])[0]
            if id_doc_unico:
                # Filet de sécurité : si le "+" est arrivé mal encodé (transformé en espace
                # par le navigateur ou une vieille version en cache), on le restaure.
                id_doc_unico = id_doc_unico.strip()
                if id_doc_unico and not id_doc_unico.startswith('+') and len(id_doc_unico) >= 12 and id_doc_unico[:3] == "258":
                    id_doc_unico = "+" + id_doc_unico

            db = firestore.client()

            # MODO ÚNICO : devolve apenas 1 condutor (usado pelo motorista.html
            # para ver o seu próprio pedido pendente, e pelo cliente para
            # acompanhar o estado da sua solicitação)
            if id_doc_unico:
                doc = db.collection("motoristas").document(str(id_doc_unico)).get()
                if not doc.exists:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"erreur": "Condutor não encontrado"}).encode('utf-8'))
                    return

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps(montar_motorista(doc)).encode('utf-8'))
                return

            if modo_admin:
                docs = db.collection("motoristas").stream()
            else:
                docs = db.collection("motoristas").where("status", "==", "disponivel").stream()

            agora = datetime.now(timezone.utc)
            lista_motoristas = []
            for doc in docs:
                m = doc.to_dict()

                if not modo_admin:
                    atualizado_em = m.get("atualizado_em")
                    if atualizado_em is not None:
                        if (agora - atualizado_em) > LIMITE_VISIBILIDADE:
                            continue

                lista_motoristas.append(montar_motorista(doc))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(json.dumps(lista_motoristas).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
                    
