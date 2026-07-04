import os
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# Initialisation de Firebase (Assure-toi que tes variables d'environnement Vercel sont configurées)
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/api/enregistrer', methods=['POST'])
def enregistrer_ou_supprimer():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400

        # CAS UNIQUE : SUPPRESSION DEPUIS LE PANNEAU CEO (action: "delete")
        if data.get("action") == "delete":
            id_doc = data.get("id_doc")
            if not id_doc:
                return jsonify({"error": "ID do documento em falta"}), 400
            
            # Suppression directe dans Firebase
            db.collection('motoristas').document(id_doc).delete()
            return jsonify({"status": "deletado", "message": "Condutor removido com sucesso"}), 200

        # CAS NORMAL : ENREGISTREMENT DU CHAUFFEURPUIS LE FORMULAIRE
        telephone = data.get("telephone")
        if not telephone:
            return jsonify({"error": "Número de telefone obrigatório"}), 400

        # Préparation du dictionnaire de données propre
        moto_data = {
            "tipo": data.get("tipo", "moto"),
            "nom": data.get("nom", "Anonimo"),
            "telephone": telephone,
            "plaque": data.get("plaque", "Sem Placa"),
            "latitude": float(data.get("latitude")),
            "longitude": float(data.get("longitude")),
            "timestamp": firestore.SERVER_TIMESTAMP
        }

        # On écrase ou on crée l'enregistrement lié à ce numéro unique
        db.collection('motoristas').document(str(telephone)).set(moto_data)
        return jsonify({"status": "sucesso", "message": "Posição gravada"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
