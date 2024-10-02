# Ajouter le chemin de `sdk` pour les modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk')))

import os
import sys
from flask import Flask, request, jsonify
from sdk.paapi5_python_sdk.api.default_api import DefaultApi
from sdk.paapi5_python_sdk.models.partner_type import PartnerType
from sdk.paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from sdk.paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from sdk.paapi5_python_sdk.rest import ApiException


# Initialisation de l'application Flask
app = Flask(__name__)

# Récupérer les variables d'environnement définies dans Google Cloud Run
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")

# Vérification que les variables d'environnement ont été récupérées correctement
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("L'une des variables d'environnement nécessaires (ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG) n'est pas définie.")

# Initialiser l'API Amazon avec les clés d'environnement
amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG)

@app.route('/search', methods=['POST'])
def amazon_search():
    # Récupérer les données envoyées dans la requête POST (ex: {"keywords": "laptop"})
    data = request.get_json()
    keywords = data.get('keywords', '')

    # Si aucun mot-clé n'est fourni, retourner une erreur
    if not keywords:
        return jsonify({"error": "Keywords are required for searching"}), 400

    try:
        # Rechercher des articles via l'API Amazon
        products = amazon.search_items(keywords=keywords, search_index="All", item_count=5)
        
        # Préparer la réponse avec les informations des produits
        results = []
        for product in products:
            results.append({
                "title": product.title,
                "url": product.detail_page_url,
                "price": product.price_and_currency
            })
        
        return jsonify(results)
    except AmazonException as e:
        # Gérer les erreurs de l'API Amazon
        return jsonify({"error": str(e)}), 500

# Lancer l'application Flask sur le port 8080 (nécessaire pour Google Cloud Run)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
