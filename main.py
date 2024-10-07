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

# Ajoutez ce print statement pour vérifier les valeurs des variables d'environnement
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
        # Create a date for headers and the credential string
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope

        # Create canonical request
        canonical_uri = self.uri
        canonical_querystring = ''
        canonical_headers = 'host:{}\nx-amz-date:{}\n'.format(self.host, amz_date)
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(self.payload.encode('utf-8')).hexdigest()
        canonical_request = '{}\n{}\n{}\n{}\n{}\n{}'.format(
            self.method, canonical_uri, canonical_querystring, canonical_headers, signed_headers, payload_hash)

        # Create the string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = '{}/{}/{}/aws4_request'.format(date_stamp, self.region, self.service)
        string_to_sign = '{}\n{}\n{}\n{}'.format(
            algorithm, amz_date, credential_scope, hashlib.sha256(canonical_request.encode('utf-8')).hexdigest())

        # Create the signing key using the function defined above.
        signing_key = self.get_signature_key(date_stamp)

        # Sign the string_to_sign using the signing_key
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # Add signing information to the request headers
        authorization_header = '{} Credential={}/{}, SignedHeaders={}, Signature={}'.format(
            algorithm, self.access_key, credential_scope, signed_headers, signature)

        headers = {
            'Authorization': authorization_header,
            'x-amz-date': amz_date,
            'Content-Type': 'application/json'
        }

        return headers

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

# Créer une instance de la classe AWSV4Signer
signer = AWSV4Signer(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    region='eu-west-1',
    service='ProductAdvertisingAPI',
    host='webservices.amazon.fr',
    method='POST',
    uri='/paapi5/searchitems',
    payload=''
)

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

        # Ajouter la signature aux en-têtes de la requête
        headers = signer.get_authorization_header()
        client.default_headers.update(headers)

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
        print(f"[ERROR] API Exception: {str(e)}")  # Ajout de log pour débogage
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[ERROR] General Exception: {str(e)}")  # Ajout de log pour débogage
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

# Lancer l'application Flask sur le port 8080 (nécessaire pour Google Cloud Run)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
