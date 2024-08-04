# import pandas as pd
# from pymongo import MongoClient
# from bson.objectid import ObjectId
# import random
# import datetime

# # MongoDB connection string
# mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject"

# # Create a MongoDB client
# mongo_client = MongoClient(mongodb_connection_string)

# # Access the specific database
# mongo_db = mongo_client["mo9695_DBProject"]
# orders_collection = mongo_db['orders']
# products_collection = mongo_db['products']

# # Read product data from the products collection
# products = list(products_collection.find({}))

# if not products:
#     raise ValueError("No products found in the database")

# # Function to generate a random datetime within the last 30 days
# def generate_random_datetime():
#     start = datetime.datetime.now() - datetime.timedelta(days=30)
#     end = datetime.datetime.now()
#     return start + (end - start) * random.random()

# # Generate new orders based on product reviews
# new_orders = []
# order_ids = set()  # To ensure unique order IDs
# for product in products:
#     seller_id = product["seller_id"]
#     for review in product.get("order_reviews", []):
#         order_id = review["order_id"]
#         if order_id not in order_ids:
#             order_ids.add(order_id)
#             customer_id = review["customer_id"]  # Use the customer ID from the review

#             # Fetch product details for order items
#             product_id = review["product_id"]
#             quantity = random.randint(1, 10)
#             price = float(product["price"])  # Convert price to float

#             total_payment_value = quantity * price

#             purchased_at = generate_random_datetime()
#             approved_at = purchased_at + datetime.timedelta(hours=random.randint(1, 48))

#             new_order = {
#                 "_id": order_id,  # Use existing order ID
#                 "customer_id_fk": customer_id,
#                 "order_status": random.choice(["paid", "unpaid"]),
#                 "payment": {
#                     "payment_type": random.choice(["Credit Card", "Visa", "Paynow"]),
#                     "payment_installments": random.randint(0, 12),
#                     "payment_value": round(total_payment_value, 2),
#                     "purchased_at": purchased_at,
#                     "approved_at": approved_at
#                 },
#                 "order_items": [
#                     {
#                         "product_id": product_id,
#                         "quantity": quantity,
#                         "name": product["name"],  # Adding the product name for the sales report
#                         "price": price,  # Adding the product price for the sales report
#                         "seller_id": seller_id  # Adding the seller_id for reference
#                     }
#                 ]
#             }

#             new_orders.append(new_order)

# # Insert new orders into MongoDB
# if new_orders:
#     orders_collection.insert_many(new_orders)
#     print(f"Inserted {len(new_orders)} new orders into the orders collection")
# else:
#     print("No new orders to insert")

import pandas as pd
from pymongo import MongoClient
from bson.objectid import ObjectId
import random
import datetime

# MongoDB connection string
mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject"

# Create a MongoDB client
mongo_client = MongoClient(mongodb_connection_string)

# Access the specific database
mongo_db = mongo_client["mo9695_DBProject"]
orders_collection = mongo_db['orders']
products_collection = mongo_db['products']

# Read product data from the products collection
products = list(products_collection.find({}))

if not products:
    raise ValueError("No products found in the database")

print(f"Retrieved {len(products)} products from the products collection")

# Function to generate a random datetime within the last 30 days
def generate_random_datetime():
    start = datetime.datetime.now() - datetime.timedelta(days=30)
    end = datetime.datetime.now()
    return start + (end - start) * random.random()

# Generate new orders based on product reviews
new_orders = []
order_ids = set()  # To ensure unique order IDs
for product in products:
    seller_id = product["seller_id"]
    for review in product.get("order_reviews", []):
        order_id = review["order_id"]
        if order_id not in order_ids:
            order_ids.add(order_id)
            customer_id = review["customer_id"]

            # Fetch product details for order items
            product_id = review["product_id"]
            quantity = random.randint(1, 10)
            price = float(product["price"])  # Convert price to float

            total_payment_value = quantity * price

            purchased_at = generate_random_datetime()
            approved_at = purchased_at + datetime.timedelta(hours=random.randint(1, 48))

            new_order = {
                "_id": order_id,  # Use existing order ID
                "customer_id_fk": customer_id,
                "order_status": random.choice(["paid", "unpaid"]),
                "payment": {
                    "payment_type": random.choice(["Credit Card", "Visa", "Paynow"]),
                    "payment_installments": random.randint(0, 12),
                    "payment_value": round(total_payment_value, 2),
                    "purchased_at": purchased_at,
                    "approved_at": approved_at
                },
                "order_items": [
                    {
                        "product_id": product_id,
                        "quantity": quantity,
                        "name": product["name"],  # Adding the product name for the sales report
                        "price": price,  # Adding the product price for the sales report
                        "seller_id": seller_id  # Adding the seller_id for reference
                    }
                ]
            }

            new_orders.append(new_order)

# Insert new orders into MongoDB
if new_orders:
    orders_collection.insert_many(new_orders)
    print(f"Inserted {len(new_orders)} new orders into the orders collection")
else:
    print("No new orders to insert")


# import pandas as pd
# from pymongo import MongoClient
# from bson.objectid import ObjectId
# import random
# import datetime

# # MongoDB connection string
# mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject"

# # Create a MongoDB client
# mongo_client = MongoClient(mongodb_connection_string)

# # Access the specific database
# mongo_db = mongo_client["mo9695_DBProject"]
# orders_collection = mongo_db['orders']
# products_collection = mongo_db['products']

# # Read product data from the products collection
# products = list(products_collection.find({}))

# if not products:
#     raise ValueError("No products found in the database")

# # Function to generate a random datetime within the last 30 days
# def generate_random_datetime():
#     start = datetime.datetime.now() - datetime.timedelta(days=30)
#     end = datetime.datetime.now()
#     return start + (end - start) * random.random()

# # Generate new orders based on product reviews
# new_orders = []
# order_ids = set()  # To ensure unique order IDs
# for product in products:
#     seller_id = product["seller_id"]
#     for review in product.get("order_reviews", []):
#         order_id = review["order_id"]
#         if order_id not in order_ids:
#             order_ids.add(order_id)
#             customer_id = int(review["customer_id"], 16) % 42 + 1  # Simulating customer IDs as integers 1-42

#             # Fetch product details for order items
#             product_id = review["product_id"]
#             quantity = random.randint(1, 10)
#             price = float(product["price"])  # Convert price to float

#             total_payment_value = quantity * price

#             purchased_at = generate_random_datetime()
#             approved_at = purchased_at + datetime.timedelta(hours=random.randint(1, 48))

#             new_order = {
#                 "_id": order_id,  # Use existing order ID
#                 "customer_id_fk": customer_id,
#                 "order_status": random.choice(["paid", "unpaid"]),
#                 "payment": {
#                     "payment_type": random.choice(["Credit Card", "Visa", "Paynow"]),
#                     "payment_installments": random.randint(0, 12),
#                     "payment_value": round(total_payment_value, 2),
#                     "purchased_at": purchased_at,
#                     "approved_at": approved_at
#                 },
#                 "order_items": [
#                     {
#                         "product_id": product_id,
#                         "quantity": quantity,
#                         "name": product["name"],  # Adding the product name for the sales report
#                         "price": price,  # Adding the product price for the sales report
#                         "seller_id": seller_id  # Adding the seller_id for reference
#                     }
#                 ]
#             }

#             new_orders.append(new_order)

# # Insert new orders into MongoDB
# if new_orders:
#     orders_collection.insert_many(new_orders)
#     print(f"Inserted {len(new_orders)} new orders into the orders collection")
# else:
#     print("No new orders to insert")
