from flask import Flask, request, jsonify
from python_amazon_paapi import AmazonApi, AmazonException

app = Flask(__name__)

# Récupérer les variables d'environnement
ACCESS_KEY = "YOUR_ACCESS_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"
ASSOCIATE_TAG = "YOUR_ASSOCIATE_TAG"
REGION = "us"  # Modifier selon ta région (ex: 'us', 'uk', etc.)

# Initialiser l'API Amazon
amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG, REGION)

@app.route('/search', methods=['POST'])
def amazon_search():
    data = request.get_json()
    keywords = data.get('keywords', '')

    try:
        # Rechercher des articles via l'API Amazon
        products = amazon.search_items(keywords=keywords, search_index="All", item_count=5)
        results = []
        for product in products:
            results.append({
                "title": product.title,
                "url": product.detail_page_url,
                "price": product.price_and_currency
            })
        return jsonify(results)
    except AmazonException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
