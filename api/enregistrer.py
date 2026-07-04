import os
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# INITIALISATION SÉCURISÉE DE FIREBASE (ANTI-BUG VERCEL)
if not firebase_admin._apps:
    try:
        # Récupération de la clé stockée dans Vercel
        raw_key = os.environ.get("FIREBASE_PRIVATE_KEY", "")
        
        # Nettoyage strict de tous les types de guillemets parasites possibles
        raw_key = raw_key.strip()
        if raw_key.startswith('"') and raw_key.endswith('"'):
            raw_key = raw_key[1:-1]
        if raw_key.startswith("'") and raw_key.endswith("'"):
            raw_key = raw_key[1:-1]
            
        # Remplacement universel des sauts de ligne corrompus
        clean_key = raw_key.replace('\\n', '\n')

        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": clean_key,
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        })
        firebase_admin.initialize_app(cred)
    except Exception as init_err:
        print(f"Erro ao inicializar Firebase: {str(init_err)}")

# Initialisation du client Firestore globale
try:
    db = firestore.client()
except Exception:
    db = None

@app.route('/api/enregistrer', methods=['POST'])
def enregistrer_ou_supprimer():
    if db is None:
        return jsonify({"error": "Banco de dados Firebase nao configurado no servidor"}), 500
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400

        # ACTION 1 : SUPPRESSION DEPUIS LE PANNEAU CEO
        if data.get("action") == "delete":
            id_doc = data.get("id_doc")
            if not id_doc:
                return jsonify({"error": "ID do documento em falta"}), 400
            
            db.collection('motoristas').document(str(id_doc)).delete()
            return jsonify({"status": "deletado", "message": "Condutor removido"}), 200

        # ACTION 2 : ENREGISTREMENT CHAUFFEUR VIA FORMULAIRE
        telephone = data.get("telephone")
        if not telephone:
            return jsonify({"error": "Numero de telefone obrigatorio"}), 400

        moto_data = {
            "tipo": data.get("tipo", "moto"),
            "nom": data.get("nom", "Anonimo"),
            "telephone": str(telephone),
            "plaque": data.get("plaque", "Sem Placa"),
            "latitude": float(data.get("latitude")),
            "longitude": float(data.get("longitude")),
            "timestamp": firestore.SERVER_TIMESTAMP
        }

        # Écrase ou crée l'enregistrement du chauffeur avec son numéro unique
        db.collection('motoristas').document(str(telephone)).set(moto_data)
        return jsonify({"status": "sucesso", "message": "Posicao gravada"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
