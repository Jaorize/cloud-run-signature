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


app = Flask(__name__)

# Fetch access key, secret key, and associate tag from environment variables
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
ASSOCIATE_TAG = os.getenv('ASSOCIATE_TAG')

# Client to be initialized once globally
client = None

def initialize_client():
    """
    Initialize the ApiClient only once globally.
    """
    global client
    if client is None:
        client = ApiClient(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            host='webservices.amazon.fr',
            region='eu-west-1'
        )

@app.route('/search', methods=['POST'])
def search_amazon_items():
    """
    Endpoint for searching Amazon items.
    Request Body: JSON object containing 'keywords'
    """
    try:
        # Extract keywords from POST request body
        data = request.get_json()
        keywords = data.get('keywords', '')

        if not keywords:
            return jsonify({"error": "Missing 'keywords' in request"}), 400

        # Initialize the Amazon API client
        initialize_client()

        # Define the resources we want to retrieve for each item
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_FEATURES,
            SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]

        # Build the search request
        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index="All",
            item_count=5,
            resources=resources
        )

        # Perform the API call
        response = client.search_items(search_request)

        # Handle response success
        if response.items_result and response.items_result.items:
            items = []
            for item in response.items_result.items:
                item_data = {
                    "title": item.item_info.title.display_value if item.item_info.title else "N/A",
                    "features": item.item_info.features.display_values if item.item_info.features else "N/A",
                    "price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else "N/A",
                    "image_url": item.images.primary.medium.url if item.images and item.images.primary.medium else "N/A"
                }
                items.append(item_data)

            return jsonify(items), 200
        else:
            return jsonify({"error": "No items found or API returned an error"}), 404

    except ApiException as e:
        return jsonify({"error": f"Amazon API Exception: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Run the Flask app, ensuring the environment variables are set
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
