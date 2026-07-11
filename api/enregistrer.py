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
    def _responder(self, status_code, payload):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if not data:
                self._responder(400, {"erreur": "Nenhum dado recebido"})
                return

            db = firestore.client()

            # ACTION A : SUPPRESSION DEFINITIVE
            if data.get("action") == "delete":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self._responder(400, {"erreur": "id_doc em falta"})
                    return

                db.collection("motoristas").document(str(id_doc)).delete()
                self._responder(200, {"status": "deletado"})
                return

            # ACTION B : ATTRIBUTION DE COURSE (DISPATCH) + HEARTBEAT DO CONDUTOR
            if data.get("action") == "assign":
                id_doc = data.get("id_doc")

                if not id_doc:
                    self._responder(400, {"erreur": "id_doc em falta"})
                    return

                update_data = {
                    "atualizado_em": firestore.SERVER_TIMESTAMP
                }

                novo_status = data.get("status")
                if novo_status:
                    update_data["status"] = novo_status

                latitude = data.get("latitude")
                longitude = data.get("longitude")
                if latitude is not None and longitude is not None:
                    try:
                        update_data["latitude"] = float(latitude)
                        update_data["longitude"] = float(longitude)
                    except (TypeError, ValueError):
                        pass

                db.collection("motoristas").document(str(id_doc)).update(update_data)
                self._responder(200, {"status": "sucesso"})
                return

            # ACTION D : REGISTO DE CONTACTO (estatística, sem identificar o cliente)
            if data.get("action") == "contato":
                id_doc = data.get("id_doc")
                tipo_contato = data.get("tipo_contato", "outro")
                if tipo_contato not in ("ligar", "whatsapp", "sms"):
                    tipo_contato = "outro"
                if not id_doc:
                    self._responder(400, {"erreur": "id_doc em falta"})
                    return

                db.collection("motoristas").document(str(id_doc)).update({
                    "contactos_total": firestore.Increment(1),
                    f"contactos_{tipo_contato}": firestore.Increment(1)
                })

                self._responder(200, {"status": "contato_registado"})
                return

            # ACTION E : CLIENTE CONTACTA UM CONDUTOR -> ABRE PEDIDO PENDENTE
            if data.get("action") == "pedido_cliente":
                id_doc = data.get("id_doc")
                cliente_lat = data.get("cliente_lat")
                cliente_lng = data.get("cliente_lng")

                if not id_doc or cliente_lat is None or cliente_lng is None:
                    self._responder(400, {"erreur": "Dados do pedido incompletos"})
                    return

                try:
                    cliente_lat = float(cliente_lat)
                    cliente_lng = float(cliente_lng)
                except (TypeError, ValueError):
                    self._responder(400, {"erreur": "Coordenadas inválidas"})
                    return

                db.collection("motoristas").document(str(id_doc)).update({
                    "cliente_pedido": {
                        "status": "pendente",
                        "cliente_lat": cliente_lat,
                        "cliente_lng": cliente_lng,
                        "atualizado_em": firestore.SERVER_TIMESTAMP
                    }
                })
                self._responder(200, {"status": "pedido_criado"})
                return

            # ACTION F : CLIENTE ATUALIZA A SUA POSIÇÃO ENQUANTO PARTILHA (heartbeat do cliente)
            if data.get("action") == "atualizar_pedido_cliente":
                id_doc = data.get("id_doc")
                cliente_lat = data.get("cliente_lat")
                cliente_lng = data.get("cliente_lng")

                if not id_doc or cliente_lat is None or cliente_lng is None:
                    self._responder(400, {"erreur": "Dados incompletos"})
                    return

                try:
                    cliente_lat = float(cliente_lat)
                    cliente_lng = float(cliente_lng)
                except (TypeError, ValueError):
                    self._responder(400, {"erreur": "Coordenadas inválidas"})
                    return

                db.collection("motoristas").document(str(id_doc)).update({
                    "cliente_pedido.cliente_lat": cliente_lat,
                    "cliente_pedido.cliente_lng": cliente_lng,
                    "cliente_pedido.atualizado_em": firestore.SERVER_TIMESTAMP
                })
                self._responder(200, {"status": "posicao_atualizada"})
                return

            # ACTION G : CONDUTOR RESPONDE (ACEITAR OU RECUSAR)
            if data.get("action") == "responder_pedido":
                id_doc = data.get("id_doc")
                resposta = data.get("resposta")

                if not id_doc or resposta not in ("aceite", "recusado"):
                    self._responder(400, {"erreur": "Resposta inválida"})
                    return

                update_data = {
                    "cliente_pedido.status": resposta,
                    "cliente_pedido.atualizado_em": firestore.SERVER_TIMESTAMP
                }

                # Se aceite, o condutor sai da lista de disponíveis (deixa de ser encontrado)
                if resposta == "aceite":
                    update_data["status"] = "em_viagem"

                db.collection("motoristas").document(str(id_doc)).update(update_data)
                self._responder(200, {"status": "resposta_registada"})
                return

            # ACTION H : CONDUTOR TERMINA A CORRIDA
            if data.get("action") == "terminar_corrida":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self._responder(400, {"erreur": "id_doc em falta"})
                    return

                db.collection("motoristas").document(str(id_doc)).update({
                    "status": "disponivel",
                    "cliente_pedido": firestore.DELETE_FIELD
                })
                self._responder(200, {"status": "corrida_terminada"})
                return

            # ACTION I : CLIENTE CANCELA O PEDIDO ANTES DE RESPOSTA (só se ainda pendente)
            if data.get("action") == "cancelar_pedido":
                id_doc = data.get("id_doc")
                if not id_doc:
                    self._responder(400, {"erreur": "id_doc em falta"})
                    return

                doc_ref = db.collection("motoristas").document(str(id_doc))
                doc = doc_ref.get()
                if doc.exists:
                    pedido = doc.to_dict().get("cliente_pedido")
                    if pedido and pedido.get("status") == "pendente":
                        doc_ref.update({"cliente_pedido": firestore.DELETE_FIELD})

                self._responder(200, {"status": "pedido_cancelado"})
                return

            # ACTION C (fallback) : REGISTO INICIAL DO CONDUTOR (ou atualização se já existir)
            telephone = data.get("telephone")
            if not telephone:
                self._responder(400, {"erreur": "telephone em falta"})
                return

            doc_ref = db.collection("motoristas").document(str(telephone))
            doc_existe = doc_ref.get().exists

            try:
                lat = float(data.get("latitude"))
                lng = float(data.get("longitude"))
            except (TypeError, ValueError):
                self._responder(400, {"erreur": "Coordenadas GPS inválidas ou em falta"})
                return

            moto_data = {
                "tipo": data.get("tipo", "moto"),
                "nom": data.get("nom", "Anonimo"),
                "telephone": str(telephone),
                "plaque": data.get("plaque", "Sem Placa"),
                "latitude": lat,
                "longitude": lng,
                "status": "disponivel",
                "atualizado_em": firestore.SERVER_TIMESTAMP
            }

            if not doc_existe:
                moto_data.update({
                    "contactos_total": 0,
                    "contactos_ligar": 0,
                    "contactos_whatsapp": 0,
                    "contactos_sms": 0
                })

            doc_ref.set(moto_data, merge=True)
            self._responder(200, {"status": "sucesso"})

        except Exception as e:
            self._responder(500, {"erreur": str(e)})
                
