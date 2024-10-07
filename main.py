import os
import sys

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

# Initialisation de l'application Flask
app = Flask(__name__)

# Récupérer les variables d'environnement définies dans Google Cloud Run
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")

# Vérification que les variables d'environnement ont été récupérées correctement
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("L'une des variables d'environnement nécessaires (ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG) n'est pas définie.")

# Ajoutez ce print statement pour vérifier les valeurs des variables d'environnement
print(f"ACCESS_KEY: {ACCESS_KEY}")
print(f"SECRET_KEY: {SECRET_KEY}")
print(f"ASSOCIATE_TAG: {ASSOCIATE_TAG}")

# Initialiser l'ApiClient avec les clés d'API
client = ApiClient(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    host='webservices.amazon.fr',  # URL d'API, ajustez selon la région
    region='eu-west-1'  # Remplacez par votre région AWS, comme 'us-west-2' ou 'eu-west-1'
)

# Ajoutez ce print statement pour vérifier les valeurs lors de l'initialisation de l'ApiClient
print(f"ApiClient initialized with access_key: {ACCESS_KEY}, secret_key: {SECRET_KEY}, host: 'webservices.amazon.fr',region: 'eu-west-1'")

# Créer une instance de l'API Amazon avec le client
amazon = DefaultApi(client)

@app.route('/search', methods=['POST'])
def amazon_search():
    # Vérifier si la requête contient des données JSON valides
    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type. Must be application/json"}), 400

    # Récupérer les données envoyées dans la requête POST
    data = request.get_json()

    # Vérifier si la récupération des données a réussi
    if data is None:
        return jsonify({"error": "Empty or invalid JSON provided"}), 400

    # Vérifier si le champ 'keywords' est présent dans les données JSON
    keywords = data.get('keywords', '')
    if not keywords:
        return jsonify({"error": "Keywords are required for searching"}), 400

    # Log pour déboguer
    print(f"[DEBUG] Received keywords: {keywords}")

    try:
        # Configurer la requête avec les ressources nécessaires
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]

        # Construire la requête pour rechercher des articles
        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index="All",
            item_count=5,
            resources=resources
        )

        # Rechercher des articles via l'API Amazon
        response = amazon.search_items(search_request)

        # Vérifier si des résultats ont été trouvés
        if response is not None and response.search_result is not None:
            results = []
            for item in response.search_result.items:
                results.append({
                    "title": item.item_info.title.display_value,
                    "url": item.detail_page_url,
                    "price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else 'N/A'
                })
            return jsonify(results)
        else:
            return jsonify({"message": "No results found"}), 404

    except ApiException as e:
        # Gérer les erreurs de l'API Amazon
        print(f"[ERROR] API Exception: {str(e)}")  # Ajout de log pour débogage
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        # Gérer les autres exceptions générales
        print(f"[ERROR] General Exception: {str(e)}")  # Ajout de log pour débogage
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

# Lancer l'application Flask sur le port 8080 (nécessaire pour Google Cloud Run)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
