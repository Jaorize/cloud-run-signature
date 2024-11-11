import os
import sys
import time
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from paapi5_python_sdk import Availability, DeliveryFlag, MinPrice

load_dotenv()  # Récupère les variables d'environnement à partir de .env.
# Ajouter le chemin SDK à PYTHONPATH
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk'))
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

# Importer les modules nécessaires du SDK
from paapi5_python_sdk.api_client import ApiClient
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException

# Initialisation de l'application Flask
app = Flask(__name__)

# Récupérer les variables d'environnement
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ASSOCIATE_TAG = os.getenv("ASSOCIATE_TAG")
HOST = 'webservices.amazon.fr'
REGION = 'eu-west-1'

# Vérifier les variables d'environnement
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
        # Définir les ressources nécessaires pour la recherche
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
            SearchItemsResource.OFFERS_LISTINGS_AVAILABILITY_TYPE,
            SearchItemsResource.OFFERS_LISTINGS_DELIVERYINFO_ISPRIMEELIGIBLE,
            SearchItemsResource.ITEMINFO_EXTERNALIDS
        ]

        total_results = []
        desired_total = 100  # Nombre total de résultats souhaité
        results_per_page = 10  # Nombre de résultats par page (maximum possible)
        pages_needed = desired_total // results_per_page  # Nombre de pages requis

        for page in range(1, pages_needed + 1):
            # Créer la requête de recherche pour chaque page
            search_request = SearchItemsRequest(
                partner_tag=ASSOCIATE_TAG,
                partner_type=PartnerType.ASSOCIATES,
                keywords=keywords,
                search_index=request.args.get('search_index', default='All'),
                item_count=results_per_page,
                item_page=page,  # Utilisation du paramètre de pagination
                resources=resources,
                availability=Availability.AVAILABLE,
                delivery_flags=[DeliveryFlag.PRIME],
                min_price=2500  # Exemple de filtre de prix pour 30 EUR minimum
            )

            # Gestion du throttling avec tentatives multiples
            attempts = 0
            max_attempts = 3
            success = False
            while attempts < max_attempts and not success:
                try:
                    # Faire la requête et récupérer la réponse
                    response = amazon_api.search_items(search_request)
                    success = True  # La requête a réussi, on peut continuer

                    # Traiter la réponse
                    if response and response.search_result and response.search_result.items:
                        results = [
                            {
                                "title": item.item_info.title.display_value,
                                "url": item.detail_page_url,
                                "price": item.offers.listings[
                                    0].price.display_amount if item.offers and item.offers.listings else 'N/A',
                                "primary_image": item.images.primary.large.url if hasattr(item, 'images') and hasattr(
                                    item.images, 'primary') and hasattr(item.images.primary, 'large') else 'N/A',
                                "ASIN": item.asin,
                                "prime_eligible": any(
                                    listing.delivery_info.is_prime_eligible
                                    for listing in item.offers.listings
                                    if listing is not None and listing.delivery_info is not None
                                ) if item.offers and item.offers.listings else False
                            }
                            for item in response.search_result.items
                            if item.offers and item.offers.listings and item.offers.listings[0].price.amount >= 25
                            # Filtre de prix en EUR
                        ]
                        total_results.extend(results)  # Ajoute les résultats de cette page

                except ApiException as e:
                    if e.status == 429:  # Code d'erreur pour "Too Many Requests"
                        print(f"[ERROR] Too Many Requests - waiting to retry (Attempt {attempts + 1}/{max_attempts})")
                        attempts += 1
                        time.sleep(10)  # Attente de 10 secondes avant de réessayer
                    else:
                        # Pour les autres types d'erreurs, sortez de la boucle
                        raise

            # Arrête la boucle si le nombre de résultats souhaité est atteint
            if len(total_results) >= desired_total:
                break

            # Pause de 5 secondes entre les pages pour éviter de saturer le service
            time.sleep(5)

        # Limite à 100 résultats uniques maximum
        total_results = total_results[:desired_total]

        # Retourne les résultats finaux sous forme de JSON
        return jsonify(total_results), 200

    except ApiException as e:
        print(f"[ERROR] API Exception: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"[ERROR] General Exception: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred. {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
