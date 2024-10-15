# main.py
import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify

# Ajouter le répertoire SDK au PYTHONPATH si nécessaire
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk'))
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

# Importer les modules du SDK après avoir ajouté le chemin
from paapi5_python_sdk.api_client import ApiClient
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException
from paapi5_python_sdk.auth.sign_helper import AWSV4Auth

# Initialisation de l'application Flask
app = Flask(__name__)

# Récupérer les variables d'environnement définies dans Google Cloud Run
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")

# Vérification que les variables d'environnement ont été récupérées correctement
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("L'une des variables d'environnement nécessaires (ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG) n'est pas définie.")

# Afficher les valeurs des variables d'environnement pour le débogage
print(f"ACCESS_KEY: {ACCESS_KEY}")
print(f"SECRET_KEY: {SECRET_KEY}")
print(f"ASSOCIATE_TAG: {ASSOCIATE_TAG}")

# Créer une instance de l'ApiClient avec la configuration initiale
client = None

def initialize_client():
    global client
    if client is None:
        client = ApiClient(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            host='webservices.amazon.fr',
            region='eu-west-1'
        )
        print(f"[DEBUG] ApiClient initialized with access_key: {client.access_key}, secret_key: {client.secret_key}")

@app.route('/search', methods=['POST'])
def amazon_search():
    initialize_client()

    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type. Must be application/json"}), 400

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Empty or invalid JSON provided"}), 400

    keywords = data.get('keywords', '')
    if not keywords:
        return jsonify({"error": "Keywords are required for searching"}), 400

    print(f"[DEBUG] Received keywords: {keywords}")

    try:
        # Définir les ressources nécessaires pour la recherche
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]

        # Créer la requête de recherche
        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index="All",
            item_count=5,
            resources=resources
        )

        # Utiliser AWSV4Auth pour générer la signature et les en-têtes d'authentification
        timestamp = datetime.utcnow()  # Correction : utiliser un objet datetime
        auth = AWSV4Auth(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            partner_tag=ASSOCIATE_TAG
            region='eu-west-1',
            service='ProductAdvertisingAPI',
            host='webservices.amazon.fr',
            method_name='POST',
            timestamp=timestamp  # Correction : passer un objet datetime
        )

        # Générer les en-têtes de la requête signée
        headers = auth.get_headers()


        # Mettre à jour les en-têtes du client API avec ceux générés
        client.default_headers.update(headers)
        print(f"[DEBUG] Headers used in request: {headers}")

        # Créer une instance de DefaultApi
        amazon_api = DefaultApi(client)

        # Effectuer la requête
        response = amazon_api.search_items(search_request)

        if response and response.search_result and response.search_result.items:
            results = [
                {
                    "title": item.item_info.title.display_value,
                    "url": item.detail_page_url,
                    "price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else 'N/A'
                }
                for item in response.search_result.items
            ]
            return jsonify(results), 200
        else:
            return jsonify({"message": "No results found"}), 404

    except ApiException as e:
        print(f"[ERROR] API Exception: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[ERROR] General Exception: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred. {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
