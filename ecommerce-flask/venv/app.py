from flask import Flask, jsonify, request
from flask_cors import CORS
from flask import render_template, url_for
import pymongo
import os
from bson import ObjectId


app = Flask(__name__, static_folder="static")
CORS(app)  # Allow frontend requests

MONGO_URI = "mongodb+srv://bakhytzhanabdilmazhit:6FcpfAMoAP95tOXK@cluster0.mlqaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)  
db = client.get_database("ecommerce")

products = {
    1: {
        "product_name": "Mingus Ah Um",
        "artist": "Charles Mingus",
        "year": 1959,
        "price": 29.99,
        "image_filename": "mingus.jpg",
        "description": "A landmark jazz album that showcases Charles Mingus' mastery of composition and improvisation."
    },
    2: {
        "product_name": "My Favorite Things",
        "artist": "John Coltrane",
        "year": 1961,
        "price": 24.99,
        "image_filename": "coltrane.jpg",
        "description": "John Coltrane’s revolutionary take on Broadway tunes, featuring his iconic modal jazz style."
    },
    3: {
        "product_name": "Chet Baker with Russ Freeman",
        "artist": "Chet Baker",
        "year": 1953,
        "price": 27.99,
        "image_filename": "baker.jpg",
        "description": "A smooth and lyrical jazz album, highlighting Chet Baker's unique trumpet and vocal style."
    }
}

@app.route('/populate-db', methods=['GET', 'POST'])
def populate_db():
    """Populate MongoDB with initial data if it's empty."""
    
    # Check if products exist
    product_count = db.products.count_documents({})
    user_count = db.users.count_documents({})
    
    print(f"Existing Products: {product_count}, Existing Users: {user_count}")

    if product_count == 0:
        products = [
            {"name": "Mingus Ah Um", "artist": "Charles Mingus", "year": 1959, "price": 29.99, "image": "mingus.jpg"},
            {"name": "My Favorite Things", "artist": "John Coltrane", "year": 1961, "price": 24.99, "image": "coltrane.jpg"},
            {"name": "Chet Baker with Russ Freeman", "artist": "Chet Baker", "year": 1953, "price": 27.99, "image": "baker.jpg"}
        ]
        db.products.insert_many(products)
        print("Inserted products successfully.")

    if user_count == 0:
        users = [
            {"name": "John Doe", "email": "john@example.com", "role": "customer"},
            {"name": "Admin User", "email": "admin@example.com", "role": "admin"}
        ]
        db.users.insert_many(users)
        print("Inserted users successfully.")

    return jsonify({"message": "Database population attempted!"})



@app.route('/')
def home():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1, "image": 1}))

    # Convert ObjectId to string for rendering
    for product in products:
        product["_id"] = str(product["_id"])
    
    return render_template('index.html', products=products)


@app.route('/product/<product_id>')
def product_page(product_id):
    product = db.products.find_one({"_id": ObjectId(product_id)})
    
    if product:
        product["_id"] = str(product["_id"])
        return render_template('product.html', **product)
    else:
        return "<h1>Product not found</h1>", 404



@app.route('/test-db')
def test_db():
    try:
        print("MongoDB Client:", client)
        print("Databases:", client.list_database_names())  # List all databases
        db.users.insert_one({"name": "Test User"})
        return jsonify({"message": "Database connection successful!"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
