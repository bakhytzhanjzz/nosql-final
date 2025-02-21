from flask import Flask, jsonify, request, render_template, url_for, redirect, session
from flask_cors import CORS
import pymongo
import os
from bson import ObjectId
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt

app = Flask(__name__, static_folder="static")
CORS(app)
app.config["JWT_SECRET_KEY"] = "12345"
jwt = JWTManager(app)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://bakhytzhanabdilmazhit:6FcpfAMoAP95tOXK@cluster0.mlqaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = pymongo.MongoClient(MONGO_URI)
db = client.get_database("ecommerce")

# indexing
try:
    db.products.create_index([("name", pymongo.TEXT), ("artist", pymongo.TEXT)], name="product_search_index", default_language="english")
    db.products.create_index([("price", pymongo.ASCENDING)], name="price_asc")
    db.users.create_index([("email", pymongo.ASCENDING)], unique=True, name="email_index")  # Enforce unique emails
    print("Indexes created successfully.")
except Exception as e:
    print(f"Error creating indexes: {e}")

@app.route('/')
def home():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1, "image": 1}))
 
    for product in products:
        product["_id"] = str(product["_id"])
    return render_template('index.html', products=products)

@app.route('/products', methods=['GET'])
def get_products():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1}))
    if not products:
        return jsonify({"message": "No products found"}), 404  
    for product in products:
        product["_id"] = str(product["_id"])
    return jsonify(products)

@app.route('/product/<product_id>')
def product_page(product_id):
    product = db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        product["_id"] = str(product["_id"])
        return render_template('product.html', **product)
    else:
        return "Product not found", 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        role = data.get("role", "customer")  # default to "customer" if not provided
        if not email or not password or not name:
            return jsonify({"error": "Name, Email, and Password fields are required"}), 400
        if db.users.find_one({"email": email}):
            return jsonify({"error": "Email already registered"}), 400

        # Hash the password before saving
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = {
            "name": name,
            "email": email,
            "password": hashed_pw,
            "role": role
        }
        db.users.insert_one(user)
        return jsonify({"message": "User registered successfully!"})

    # Render the registration page for GET requests
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.json
            print(f"🔍 Debug: Received Login Request Data: {data}")  # Debugging
            if not data or "email" not in data or "password" not in data:
                print("❌ Debug: Missing Email or Password in Request")
                return jsonify({"error": "Missing email or password"}), 400

            email = data.get("email")
            password = data.get("password")
            print(f"🔍 Debug: Attempting Login for {email}")  # Debugging

            user = db.users.find_one({"email": email})

            if user:
                stored_password = user["password"]
                print(f"🔍 Debug: Stored Password in DB: {stored_password}")  # Debugging
                # Ensure stored password is bytes before checking
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    print("✅ Password Matched!")  # Debugging
                    token = create_access_token(identity={"email": user["email"], "role": user["role"]})
                    return jsonify({
                        "token": token,
                        "user": {
                            "name": user["name"],
                            "email": user["email"],
                            "role": user["role"]
                        }
                    })
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
            else:
                return jsonify({"error": "User not found"}), 401

        except Exception as e:
            return jsonify({"error": "Server error"}), 500

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('token', None)
    session.pop('user', None)
    return redirect('/')

@app.route('/admin')
def admin_dashboard():
    users = list(db.users.find({}, {"_id": 1, "name": 1, "email": 1, "role": 1}))
    for user in users:
        user["_id"] = str(user["_id"])
    return render_template('admin.html', users=users)

@app.route('/admin/users', methods=['GET'])
def get_users():
    users = list(db.users.find({}, {"_id": 1, "name": 1, "email": 1, "role": 1}))
    if not users:
        return jsonify({"message": "No users found"}), 404 
    for user in users:
        user["_id"] = str(user["_id"])
    return jsonify(users)

@app.route('/admin/update-user/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    data = request.json
    new_role = data.get("role") 
    if not new_role:
        return jsonify({"message": "New role is required"}), 400

    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": new_role}}) 
    return jsonify({"message": "User updated successfully!"})

@app.route('/admin/delete-user/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    db.users.delete_one({"_id": ObjectId(user_id)})
    return jsonify({"message": "User deleted!"})

@app.route('/admin/add-product', methods=['POST'])
@jwt_required()
def add_product():
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    data = request.json
    try:
        if not all(k in data for k in ("name", "artist", "year", "price")):
            return jsonify({"message": "Missing required fields"}), 400
        data["year"] = int(data["year"])  # try converting to integer
        data["price"] = float(data["price"])  # try converting to float
        product_id = db.products.insert_one(data).inserted_id
        return jsonify({"message": "Product added!", "product_id": str(product_id)})
    except ValueError:
        return jsonify({"message": "Invalid year or price format"}), 400
    except Exception as e:
        return jsonify({"message": f"Error adding product: {str(e)}"}), 500

@app.route('/admin/update-product/<product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    data = request.json
    try:
        # Validate data types if they are present in the request
        if "year" in data:
            data["year"] = int(data["year"])
        if "price" in data:
            data["price"] = float(data["price"])
        result = db.products.update_one({"_id": ObjectId(product_id)}, {"$set": data})
        if result.modified_count > 0:
            return jsonify({"message": "Product updated successfully!"})
        else:
            return jsonify({"message": "Product not found or no changes applied."}), 404
    except ValueError:
        return jsonify({"message": "Invalid year or price format"}), 400
    except Exception as e:
        return jsonify({"message": f"Error updating product: {str(e)}"}), 500

@app.route('/admin/delete-product/<product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    result = db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Product deleted!"})
    else:
        return jsonify({"message": "Product not found."}), 404

@app.route('/order', methods=['POST'])
@jwt_required()
def place_order():
    """Place an order (Customer Only)."""
    current_user = get_jwt_identity()
    data = request.json
    product_names = data.get("products")  
    if not product_names or not isinstance(product_names, list):
        return jsonify({"message": "Products list is required"}), 400
    product_ids = []
    for name in product_names:
        product = db.products.find_one({"name": name}, {"_id": 1})
        if product:
            product_ids.append(product["_id"])
        else:
            return jsonify({"message": f"Product '{name}' not found"}), 404 

    order = {
        "user_email": current_user["email"],
        "product_ids": product_ids,
        "status": "Pending",
        "order_date": pymongo.InsertOne(datetime.datetime.utcnow()) 
    }
    try:
        order_id = db.orders.insert_one(order).inserted_id
        return jsonify({"message": "Order placed!", "order_id": str(order_id)})
    except Exception as e:
        return jsonify({"message": f"Could not place order: {str(e)}"}), 500

@app.route('/my-orders', methods=['GET'])
@jwt_required()
def my_orders():
    current_user = get_jwt_identity()
    orders = list(db.orders.find({"user_email": current_user["email"]}))
    for order in orders:
        order["_id"] = str(order["_id"])
        product_names = []
        for product_id in order["product_ids"]:
            product = db.products.find_one({"_id":product_id},{"name":1})
            if product:
                product_names.append(product["name"]) 
            else:
                product_names.append("Unknown Product") 
        order["products"] = product_names 

    return jsonify(orders)

@app.route('/test-db')
def test_db():
    try:
        print("MongoDB Client:", client)
        print("Databases:", client.list_database_names())  
        if not db.users.find_one({"name": "Test User"}):
            db.users.insert_one({"name": "Test User"})
        return jsonify({"message": "Database connection successful!"})
    except Exception as e:
        return jsonify({"error": str(e)})

# ublk operations
@app.route('/admin/bulk-add-products', methods=['POST'])
@jwt_required()
def bulk_add_products():
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    products = request.json  
    if not isinstance(products, list):
        return jsonify({"message": "Expected a list of products"}), 400
    try:
        for product in products:
            if not all(k in product for k in ("name", "artist", "year", "price")):
                return jsonify({"message": "Missing required fields in one or more products"}), 400
            product["year"] = int(product["year"])
            product["price"] = float(product["price"])

        bulk_operations = [pymongo.InsertOne(product) for product in products]
        result = db.products.bulk_write(bulk_operations)
        return jsonify({"message": f"Successfully added {result.inserted_count} products"}), 201
    except ValueError:
        return jsonify({"message": "Invalid year or price format in one or more products"}), 400
    except Exception as e:
        return jsonify({"message": f"Error adding products: {str(e)}"}), 500

# aggretation
@app.route('/admin/product-stats', methods=['GET'])
@jwt_required()
def get_product_stats():
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403
    try:
        pipeline = [
            {"$group": {"_id": "$artist", "total_products": {"$sum": 1}, "avg_price": {"$avg": "$price"}}},
            {"$sort": {"total_products": -1}},
            {"$limit": 10}  
        ]
        artist_stats = list(db.products.aggregate(pipeline))
        return jsonify(artist_stats)
    except Exception as e:
        return jsonify({"message": f"Error generating product stats: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(debug=True)
