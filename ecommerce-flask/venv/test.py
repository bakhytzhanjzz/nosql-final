import pymongo

MONGO_URI = "mongodb+srv://bakhytzhanabdilmazhit:6FcpfAMoAP95tOXK@cluster0.mlqaf.mongodb.net/ecommerce?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client.ecommerce

# Fetch all users
users = list(db.users.find({}, {"_id": 1, "name": 1, "email": 1, "role": 1}))
print("Users:", users)

# Fetch all products
products = list(db.products.find({}, {"_id": 1, "name": 1, "artist": 1, "year": 1, "price": 1}))
print("Products:", products)
