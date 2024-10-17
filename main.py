import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.
# Add SDK path to PYTHONPATH
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk'))
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

# Import necessary modules from SDK
from paapi5_python_sdk.api_client import ApiClient
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException

# Initialize Flask app
app = Flask(__name__)

# Retrieve environment variables
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")

# Check environment variables
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("Missing ACCESS_KEY, SECRET_KEY, or ASSOCIATE_TAG.")

# Log retrieved environment variables for debugging
print(f"ACCESS_KEY: {ACCESS_KEY}")
print(f"SECRET_KEY: {SECRET_KEY}")
print(f"ASSOCIATE_TAG: {ASSOCIATE_TAG}")

# Initialize API client
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
        print(f"[DEBUG] ApiClient initialized with access_key: {ACCESS_KEY}")

@app.route('/search', methods=['GET'])
def amazon_search():
    initialize_client()

    # if not request.is_json:
    #     return jsonify({"error": "Invalid Content-Type. Must be application/json"}), 400

    # data = request.get_json()
    # if data is None:
    #     return jsonify({"error": "Empty or invalid JSON provided"}), 400
    keywords = "laptop"
    # keywords = data.get('keywords', '')
    # if not keywords:
    #     return jsonify({"error": "Keywords are required for searching"}), 400

    print(f"[DEBUG] Received keywords: {keywords}")

    try:
        # Define the resources needed for search
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]

        # Create the search request
        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index="All",
            item_count=5,
            resources=resources
        )

        # Initialize the DefaultApi client
        amazon_api = DefaultApi(api_client=client)

        # Make the request and fetch the response
        response = amazon_api.search_items(search_request)

        # Process the response
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
