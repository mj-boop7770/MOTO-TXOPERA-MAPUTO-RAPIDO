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
    def do_POST(self):
        try:
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

            # ACTION A : SUPPRESSION DEFINITIVE
            if data.get("action") == "delete":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self.send_response(400)
                    self.end_headers()
                    return
                
                db.collection("motoristas").document(str(id_doc)).delete()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "deletado"}).encode('utf-8'))
                return

            # ACTION B : ATTRIBUTION DE COURSE (DISPATCH)
            if data.get("action") == "assign":
                id_doc = data.get("id_doc")
                novo_status = data.get("status", "em_viagem") # "em_viagem" ou "disponivel" pour le reset
                
                if not id_doc:
                    self.send_response(400)
                    self.end_headers()
                    return
                
                # Mise à jour dynâmica do status + refresca o timestamp
                # (assim um "Repor Disponível" manual também reinicia o cronómetro das 2h)
                db.collection("motoristas").document(str(id_doc)).update({
                    "status": novo_status,
                    "atualizado_em": firestore.SERVER_TIMESTAMP
                })

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "sucesso", "motorista_status": novo_status}).encode('utf-8'))
                return

            # ACTION D : REGISTO DE CONTACTO (estatística, sem identificar o cliente)
            if data.get("action") == "contato":
                id_doc = data.get("id_doc")
                tipo_contato = data.get("tipo_contato", "outro")
                if tipo_contato not in ("ligar", "whatsapp", "sms"):
                    tipo_contato = "outro"
                if not id_doc:
                    self.send_response(400)
                    self.end_headers()
                    return

                db.collection("motoristas").document(str(id_doc)).update({
                    "contactos_total": firestore.Increment(1),
                    f"contactos_{tipo_contato}": firestore.Increment(1)
                })

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "contato_registado"}).encode('utf-8'))
                return

            # ACTION C : ENREGISTREMENT INITIAL CHAUFFEUR (ou actualização se já existir)
            telephone = data.get("telephone")
            if not telephone:
                self.send_response(400)
                self.end_headers()
                return

            doc_ref = db.collection("motoristas").document(str(telephone))
            doc_existe = doc_ref.get().exists

            moto_data = {
                "tipo": data.get("tipo", "moto"),
                "nom": data.get("nom", "Anonimo"),
                "telephone": str(telephone),
                "plaque": data.get("plaque", "Sem Placa"),
                "latitude": float(data.get("latitude")),
                "longitude": float(data.get("longitude")),
                "status": "disponivel",
                "atualizado_em": firestore.SERVER_TIMESTAMP
            }

            # Só inicializa os contadores de contacto na primeira vez;
            # se o condutor já existia, não apagamos o histórico dele.
            if not doc_existe:
                moto_data.update({
                    "contactos_total": 0,
                    "contactos_ligar": 0,
                    "contactos_whatsapp": 0,
                    "contactos_sms": 0
                })

            doc_ref.set(moto_data, merge=True)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "sucesso"}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erreur": str(e)}).encode('utf-8'))
