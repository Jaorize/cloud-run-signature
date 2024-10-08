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
        date_stamp = t.strftime('%Y%m%d')  # Date sans l'heure, utilisé dans la portée des informations d'identification

        # Create canonical request
        canonical_uri = self.uri
        canonical_querystring = ''
        canonical_headers = f'host:{self.host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'
        payload_hash = hashlib.sha256(self.payload.encode('utf-8')).hexdigest()
        canonical_request = f'{self.method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

        # Create the string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{self.service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'

        # Create the signing key using the function defined above.
        signing_key = self.get_signature_key(date_stamp)

        # Sign the string_to_sign using the signing_key
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # Add signing information to the request headers
        authorization_header = f'{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'

        headers = {
            'Authorization': authorization_header,
            'x-amz-date': amz_date,
            'Content-Type': 'application/json'
        }

        return headers

# Créer une instance de l'ApiClient avec la configuration initiale
client = None

def initialize_client():
    global client
    if client is None:
        if not ACCESS_KEY or not SECRET_KEY:
            raise ValueError("ACCESS_KEY ou SECRET_KEY sont manquants")

        client = ApiClient(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            host='webservices.amazon.fr',
            region='eu-west-1'
        )
        print(f"[DEBUG] ApiClient initialized with access_key: {client.access_key}, secret_key: {client.secret_key}, host: 'webservices.amazon.fr', region: 'eu-west-1'")
    else:
        # Vérifiez que les clés n'ont pas été réinitialisées à None
        if not client.access_key or not client.secret_key:
            print(f"[ERROR] Client keys are missing! Reinitializing ApiClient.")
            client.access_key = ACCESS_KEY
            client.secret_key = SECRET_KEY
            print(f"[DEBUG] Reinitialized ApiClient with access_key: {client.access_key}, secret_key: {client.secret_key}")

@app.route('/search', methods=['POST'])
def amazon_search():
    initialize_client()  # S'assurer que le client est initialisé correctement avant chaque requête

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

        signer.payload = search_request.to_str()  # Mettre à jour le payload avec le contenu de la requête
        headers = signer.get_authorization_header()
        client.default_headers.update(headers)

        response = amazon.search_items(search_request)

