            novo_motorista = {
                "tipo": dados.get("tipo"),
                "nom": dados.get("nom"),
                "telephone": dados.get("telephone"),
                "plaque": dados.get("plaque"),
                "latitude": dados.get("latitude", 0),
                "longitude": dados.get("longitude", 0),
                "status": "disponivel",
                "registrado_em": firestore.SERVER_TIMESTAMP
            }
