from flask import Flask, jsonify, request, render_template, url_for, redirect, session
from flask_cors import CORS
import pymongo
import os
from bson import ObjectId
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt



app = Flask(__name__, static_folder="static")
CORS(app)  # Allow frontend requests

app.config["JWT_SECRET_KEY"] = "12345"
jwt = JWTManager(app)

MONGO_URI = "mongodb+srv://bakhytzhanabdilmazhit:6FcpfAMoAP95tOXK@cluster0.mlqaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)  
db = client.get_database("ecommerce")

@app.route('/')
def home():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1, "image": 1}))

    # Convert ObjectId to string for rendering
    for product in products:
        product["_id"] = str(product["_id"])
    
    return render_template('index.html', products=products)

@app.route('/products', methods=['GET'])
def get_products():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1}))
    
    if not products:
        return jsonify({"message": "No products found"}), 404  # Avoid empty response error
    
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
        return "<h1>Product not found</h1>", 404
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json

        # Ensure all fields are provided
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        role = data.get("role", "customer")  # Default to "customer" if not provided

        if not email or not password or not name or not role:
            return jsonify({"error": "All fields (name, email, password, role) are required"}), 400

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
                    print("❌ Debug: Password Mismatch!")  # Debugging

            print("❌ Debug: Invalid credentials")  # Debugging
            return jsonify({"error": "Invalid credentials"}), 401

        except Exception as e:
            print(f"❌ Debug: Error in Login Route: {e}")  # Debugging
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
        return jsonify({"message": "No users found"}), 404  # Avoid empty response error
    
    for user in users:
        user["_id"] = str(user["_id"])
    
    return jsonify(users)




@app.route('/admin/update-user/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": data.get("role")}})
    
    return jsonify({"message": "User updated successfully!"})


@app.route('/admin/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    db.users.delete_one({"_id": ObjectId(user_id)})
    return jsonify({"message": "User deleted!"})




@app.route('/admin/add-product', methods=['POST'])
def add_product():
    data = request.json
    product_id = db.products.insert_one(data).inserted_id
    
    return jsonify({"message": "Product added!", "product_id": str(product_id)})



@app.route('/admin/update-product/<product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    db.products.update_one({"_id": ObjectId(product_id)}, {"$set": data})
    
    return jsonify({"message": "Product updated successfully!"})


@app.route('/admin/delete-product/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    db.products.delete_one({"_id": ObjectId(product_id)})
    return jsonify({"message": "Product deleted!"})



@app.route('/order', methods=['POST'])
@jwt_required()
def place_order():
    """Place an order (Customer Only)."""
    current_user = get_jwt_identity()
    
    data = request.json
    order = {
        "user_email": current_user["email"],
        "products": data.get("products"), 
        "status": "Pending"
    }
    
    order_id = db.orders.insert_one(order).inserted_id
    return jsonify({"message": "Order placed!", "order_id": str(order_id)})


@app.route('/my-orders', methods=['GET'])
@jwt_required()
def my_orders():
    current_user = get_jwt_identity()
    
    orders = list(db.orders.find({"user_email": current_user["email"]}))
    
    for order in orders:
        order["_id"] = str(order["_id"])
    
    return jsonify(orders)




@app.route('/test-db')
def test_db():
    try:
        print("MongoDB Client:", client)
        print("Databases:", client.list_database_names())  # List all databases
        if not db.users.find_one({"name": "Test User"}):
            db.users.insert_one({"name": "Test User"})
        return jsonify({"message": "Database connection successful!"})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True)
