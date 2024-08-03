import pandas as pd
from pymongo import MongoClient
import random
from bson import ObjectId
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
product_prices = {product["_id"]: product["price"] for product in existing_products}

# Function to generate new order IDs and product IDs and Review IDs
def generate_order_id():
    return str(ObjectId())

def generate_product_id():
    return random.choice(product_ids)


# Function to generate a random datetime within the last 30 days
def generate_random_datetime():
    start = datetime.datetime.now() - datetime.timedelta(days=30)
    end = datetime.datetime.now()
    return start + (end - start) * random.random()

# Function to generate review data
def generate_review(product_id, customer_id):
    review_id = ObjectId()
    score = round(random.uniform(1.0, 5.0), 1)  # Random score between 1.0 and 5.0

    if score >= 4.5:
        title = "Excellent"
        content = "This product is amazing!"
    elif score >= 3.5:
        title = "Very Good"
        content = "Very satisfied with the quality."
    elif score >= 2.5:
        title = "Good"
        content = "Good value for money."
    elif score >= 1.5:
        title = "Average"
        content = "Not as expected."
    else:
        title = "Poor"
        content = "Would not recommend."

    review_date = datetime.datetime.now()

    review = {
        "_id": review_id,
        "product_id_fk": product_id,
        "customer_id": customer_id,
        "order": order_id,
        "score": score,  # Ensure score is a double
        "title": title,
        "content": content,
        "created_at": review_date
    }

    return review

# Function to embed reviews into the products collection
def embed_reviews_into_products():
    # Fetch all product IDs
    products = list(products_collection.find({}, {"_id": 1}))
    
    if not products:
        raise ValueError("No products found in the database")

    for product in products:
        product_id = product["_id"]
        customer_id = str(ObjectId())  # Simulating customer IDs as new ObjectIds

        # Generate a random number of reviews for each product
        num_reviews = random.randint(1, 5)

        reviews = [generate_review(product_id, customer_id) for _ in range(num_reviews)]

        # Update the product document with the embedded reviews
        products_collection.update_one(
            {"_id": product_id},
            {"$push": {"order_reviews": {"$each": reviews}}}
        )

    print("Reviews embedded into products successfully")

# Function to generate new orders
def generate_orders():
    new_orders = []
    for i in range(100):  # Generate 5 new orders
        order_id = ObjectId()
        customer_id = str(ObjectId())  # Simulating customer IDs as new ObjectIds

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
                "payment_type": random.choice(["credit_card", "paypal", "bank_transfer"]),
                "payment_installments": random.randint(0, 12),
                "payment_value": round(total_payment_value, 2),
                "purchased_at": purchased_at,
                "approved_at": approved_at
            },
            "order_items": order_items
        }

        new_orders.append(new_order)

    # Insert new orders into MongoDB
    orders_collection.insert_many(new_orders)

    print("New orders inserted successfully")

# Run the seeders
embed_reviews_into_products()
generate_orders()
