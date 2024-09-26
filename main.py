import os
from flask import Flask, request, jsonify
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException

app = Flask(__name__)

# Récupérer les variables d'environnement pour plus de sécurité
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")
API_HOST = "webservices.amazon.fr"
API_REGION = "eu-west-1"

# Initialisation de l'API Amazon PAAPI avec les variables d'environnement
def get_amazon_api_client():
    return DefaultApi(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        host=API_HOST,
        region=API_REGION
    )

@app.route('/search', methods=['POST'])
def amazon_api():
    data = request.get_json()

    # Récupérer les mots-clés et autres paramètres depuis la requête
    keywords = data.get('keywords', '')
    search_index = data.get('search_index', 'All')  # Défaut à 'All' si non spécifié
    item_count = data.get('item_count', 1)  # Par défaut, retourner un seul résultat

    # Sélectionner les ressources voulues dans la réponse
    search_items_resource = [
        SearchItemsResource.ITEMINFO_TITLE,
        SearchItemsResource.OFFERS_LISTINGS_PRICE
    ]

    # Initialisation de la requête Amazon PA API
    try:
        search_items_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=moto,
            search_index=All,
            item_count=10,
            resources=search_items_resource,
        )
    except ValueError as e:
        return jsonify({"error": f"Error in forming SearchItemsRequest: {str(e)}"}), 400

    # Appel à l'API Amazon
    try:
        amazon_api_client = get_amazon_api_client()
        response = amazon_api_client.search_items(search_items_request)

        if response.search_result:
            items = response.search_result.items
            results = []
            for item in items:
                item_info = {
                    "ASIN": item.asin,
                    "Title": item.item_info.title.display_value if item.item_info and item.item_info.title else "N/A",
                    "DetailPageURL": item.detail_page_url,
                    "Price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else "N/A"
                }
                results.append(item_info)
            
            return jsonify({"results": results})

        elif response.errors:
            error_message = f"Error code: {response.errors[0].code}, message: {response.errors[0].message}"
            return jsonify({"error": error_message}), 400

    except ApiException as e:
        return jsonify({"error": f"Error calling Amazon PA API: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
