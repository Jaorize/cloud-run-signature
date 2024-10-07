import os
import sys
import hashlib
import hmac
from datetime import datetime
from flask import Flask, request, jsonify

# Ajouter le répertoire SDK au PYTHONPATH si nécessaire
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk'))
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

from paapi5_python_sdk.api_client import ApiClient
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException

# Initialize Flask application
app = Flask(__name__)

# Retrieve environment variables
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")

# Validate environment variables
if not ACCESS_KEY or not SECRET_KEY or not ASSOCIATE_TAG:
    raise ValueError("Missing required environment variables: ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG")

# Create API client instance with correct credentials and configuration
client = ApiClient(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    host='webservices.amazon.fr',  # Set according to your region
    region='eu-west-1'
)

# Initialize Amazon Product API
amazon_api = DefaultApi(client)

# Signature class for request signing
class AWSV4Signer:
    def __init__(self, access_key, secret_key, region, service, host, method, uri, payload=''):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.host = host
        self.method = method
        self.uri = uri
        self.payload = payload

    def sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def get_signature_key(self, date_stamp):
        k_date = self.sign(('AWS4' + self.secret_key).encode('utf-8'), date_stamp)
        k_region = self.sign(k_date, self.region)
        k_service = self.sign(k_region, self.service)
        k_signing = self.sign(k_service, 'aws4_request')
        return k_signing

    def get_authorization_header(self):
        # Current date for header and credential
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        # Canonical request
        canonical_uri = self.uri
        canonical_querystring = ''
        canonical_headers = f'host:{self.host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(self.payload.encode('utf-8')).hexdigest()
        canonical_request = f'{self.method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

        # String to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{self.service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'

        # Generate signature
        signing_key = self.get_signature_key(date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # Authorization header
        authorization_header = f'{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        headers = {
            'Authorization': authorization_header,
            'x-amz-date': amz_date,
            'Content-Type': 'application/json'
        }

        return headers

# Create a new signer instance
signer = AWSV4Signer(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    region='eu-west-1',
    service='ProductAdvertisingAPI',
    host='webservices.amazon.fr',
    method='POST',
    uri='/paapi5/searchitems'
)

@app.route('/search', methods=['POST'])
def amazon_search():
    # Validate request content type
    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type. Must be application/json"}), 400

    # Retrieve request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty or invalid JSON provided"}), 400

    # Extract keywords from request
    keywords = data.get('keywords', '')
    if not keywords:
        return jsonify({"error": "Keywords are required for searching"}), 400

    try:
        # Configure search request
        resources = [
            SearchItemsResource.ITEMINFO_TITLE,
            SearchItemsResource.ITEMINFO_BYLINEINFO,
            SearchItemsResource.OFFERS_LISTINGS_PRICE
        ]

        search_request = SearchItemsRequest(
            partner_tag=ASSOCIATE_TAG,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keywords,
            search_index="All",
            item_count=5,
            resources=resources
        )

        # Update signer payload and headers
        signer.payload = search_request.to_str()
        headers = signer.get_authorization_header()
        client.default_headers.update(headers)

        # Make request to Amazon API
        response = amazon_api.search_items(search_request)

        # Parse and return response
        if response and response.search_result:
            items = [
                {
                    "title": item.item_info.title.display_value,
                    "url": item.detail_page_url,
                    "price": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else 'N/A'
                }
                for item in response.search_result.items
            ]
            return jsonify(items)
        else:
            return jsonify({"message": "No results found"}), 404

    except ApiException as e:
        return jsonify({"error": f"API Error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"General Error: {e}"}), 500

# Run Flask application on port 8080
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
