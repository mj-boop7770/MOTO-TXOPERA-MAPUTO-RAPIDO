import os
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# INITIALISATION SÉCURISÉE DE FIREBASE
if not firebase_admin._apps:
    try:
        # Récupération et nettoyage strict de la clé privée pour éviter le crash Vercel
        raw_key = os.environ.get("FIREBASE_PRIVATE_KEY", "")
        
        # On retire les guillemets de sécurité si Vercel en a ajouté autour de la clé
        if raw_key.startswith('"') and raw_key.endswith('"'):
            raw_key = raw_key[1:-1]
        
        # On s'assure que les sauts de ligne \n sont correctement interprétés
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
        print(f"Erreur d'initialisation Firebase: {str(init_err)}")

# Initialisation du client Firestore hors du bloc pour qu'il soit global
try:
    db = firestore.client()
except Exception:
    db = None

@app.route('/api/enregistrer', methods=['POST'])
def enregistrer_ou_supprimer():
    if db is None:
        return jsonify({"error": "Firebase nao inicializado corretamente no servidor"}), 500
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400

        # 1. CAS DE LA SUPPRESSION (Bouton ❌ du panneau admin)
        if data.get("action") == "delete":
            id_doc = data.get("id_doc")
            if not id_doc:
                return jsonify({"error": "ID do documento em falta"}), 400
            
            db.collection('motoristas').document(str(id_doc)).delete()
            return jsonify({"status": "deletado", "message": "Condutor removido com sucesso"}), 200

        # 2. CAS DE L'ENREGISTREMENT (Formulaire chauffeur)
        telephone = data.get("telephone")
        if not telephone:
            return jsonify({"error": "Número de telefone obrigatório"}), 400

        moto_data = {
            "tipo": data.get("tipo", "moto"),
            "nom": data.get("nom", "Anonimo"),
            "telephone": str(telephone),
            "plaque": data.get("plaque", "Sem Placa"),
            "latitude": float(data.get("latitude")),
            "longitude": float(data.get("longitude")),
            "timestamp": firestore.SERVER_TIMESTAMP
        }

        # On utilise le téléphone comme ID unique pour écraser l'ancienne position
        db.collection('motoristas').document(str(telephone)).set(moto_data)
        return jsonify({"status": "sucesso", "message": "Posição gravada"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
