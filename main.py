# Fichier : main.py

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

print(f"ACCESS_KEY: {ACCESS_KEY}")
print(f"SECRET_KEY: {SECRET_KEY}")
print(f"ASSOCIATE_TAG: {ASSOCIATE_TAG}")

# Classe pour gérer la signature AWS Signature Version 4
class AWSV4Signer:
    def __init__(self, access_key, secret_key, region, service, host, method, uri, payload):
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
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        canonical_uri = self.uri
        canonical_querystring = ''
        canonical_headers = f'host:{self.host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(self.payload.encode('utf-8')).hexdigest()
        canonical_request = f'{self.method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{self.service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'

        signing_key = self.get_signature_key(date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = f'{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'

        headers = {
            'Authorization': authorization_header,
            'x-amz-date': amz_date,
            'Content-Type': 'application/json'
        }

        return headers

# Créer une instance de l'ApiClient avec la configuration initiale
client = None
signer = None

def initialize_client():
    global client, signer
    if client is None:
        client = ApiClient(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            host='webservices.amazon.fr',
            region='eu-west-1'
        )
        print(f"[DEBUG] ApiClient initialized with access_key: {client.access_key}, secret_key: {client.secret_key}")

    if signer is None:
        signer = AWSV4Signer(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            region='eu-west-1',
            service='ProductAdvertisingAPI',
            host='webservices.amazon.fr',
            method='POST',
            uri='/paapi5/searchitems',
            payload=''  # Ce champ sera mis à jour avec le payload réel lors de la requête
        )

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

        signer.payload = search_request.to_str()
        headers = signer.get_authorization_header()
        client.default_headers.update(headers)

        # Log des en-têtes ajoutés pour vérifier la signature et l'horodatage
        print(f"[DEBUG] Headers used in request: {client.default_headers}")

        amazon_api = DefaultApi(client)
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
