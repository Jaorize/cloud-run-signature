import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from paapi5_python_sdk import Availability, DeliveryFlag

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
HOST='webservices.amazon.fr'
REGION='eu-west-1'

# Check environment variables
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("Missing ACCESS_KEY, SECRET_KEY, or ASSOCIATE_TAG.")

@app.route('/search', methods=['GET'])
def amazon_search():
    amazon_api = DefaultApi(
        access_key=ACCESS_KEY, secret_key=SECRET_KEY, host=HOST, region=REGION
    )

    keywords = request.args.get('keywords')
    if not keywords:
        raise ValueError("Missing keywords.")

    print(f"[DEBUG] Received keywords: {keywords}")

    try:
        # Define the resources needed for search
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE,
            SearchItemsResource.OFFERS_LISTINGS_CONDITION,
            SearchItemsResource.ITEMINFO_CLASSIFICATIONS,
            SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
            SearchItemsResource.IMAGES_PRIMARY_LARGE,
            SearchItemsResource.BROWSENODEINFO_WEBSITESALESRANK,
            SearchItemsResource.CUSTOMERREVIEWS_COUNT,
            SearchItemsResource.OFFERS_LISTINGS_AVAILABILITY_TYPE
        ]

        # Create the search request
        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index=request.args.get('search_index',default='All'),
            item_count=10,
            resources=resources,
            availability=Availability.AVAILABLE,


        )



        # Make the request and fetch the response
        response = amazon_api.search_items(search_request)

        # Process the response
        if response and response.search_result and response.search_result.items:
            results = [
                {
                    "title": item.item_info.title.display_value,
                    "url": item.detail_page_url,
                    "price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else 'N/A',
                    "primary_image": item.images.primary.large.url if hasattr(item, 'images') and hasattr(item.images, 'primary') and hasattr(item.images.primary, 'large') else 'N/A',

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
