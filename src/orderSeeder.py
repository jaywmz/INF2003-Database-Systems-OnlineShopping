import pandas as pd
from pymongo import MongoClient
import random
from bson.objectid import ObjectId
import datetime

# MongoDB connection string
mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject"

# Create a MongoDB client
mongo_client = MongoClient(mongodb_connection_string)

# Access the specific database
mongo_db = mongo_client["mo9695_DBProject"]
orders_collection = mongo_db['orders']
products_collection = mongo_db['products']

# Read product IDs and prices from the products collection
existing_products = list(products_collection.find({}, {"_id": 1, "price": 1}))

if not existing_products:
    raise ValueError("No products found in the database")

product_ids = [product["_id"] for product in existing_products]
# product_prices = {product["_id"]: product["price"] for product in existing_products}
product_prices = {product["_id"]: float(product["price"]) for product in existing_products}

# Function to generate new order IDs and product IDs
def generate_order_id():
    return str(ObjectId())

def generate_product_id():
    return random.choice(product_ids)

# Function to generate a random datetime within the last 30 days
def generate_random_datetime():
    start = datetime.datetime.now() - datetime.timedelta(days=30)
    end = datetime.datetime.now()
    return start + (end - start) * random.random()

# Generate new orders
new_orders = []
for i in range(200):  # Generate 5 new orders
    order_id = ObjectId()
    customer_id = random.randint(1, 42)  # Random customer ID

    # Generate random products for the order
    num_products = random.randint(1, 5)
    order_items = []
    total_payment_value = 0
    for _ in range(num_products):
        product_id = generate_product_id()
        quantity = random.randint(1, 10)
        price = product_prices[product_id]
        total_payment_value += quantity * price

        order_items.append({
            "product_id": product_id,
            "quantity": quantity
        })

    purchased_at = generate_random_datetime()
    approved_at = purchased_at + datetime.timedelta(hours=random.randint(1, 48))

    new_order = {
        "_id": order_id,  # New unique ID for MongoDB
        "customer_id_fk": customer_id,
        "order_status": random.choice(["paid", "unpaid"]),
        "payment": {
            "payment_type": random.choice(["credit_card", "paypal", "paynow"]),
            "payment_installments": random.randint(0, 12),
            "payment_value": round(total_payment_value, 2),
            "purchased_at": purchased_at,
            "approved_at": approved_at
        },
        "order_items": order_items
    }

    new_orders.append(new_order)

new_orders_df = pd.DataFrame(new_orders)
print("New Orders:")
print(new_orders_df)

# Insert new orders into MongoDB
orders_collection.insert_many(new_orders)

print("New orders inserted successfully")