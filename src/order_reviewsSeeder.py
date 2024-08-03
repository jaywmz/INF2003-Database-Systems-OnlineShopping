from pymongo import MongoClient, UpdateOne
from bson import ObjectId
import datetime
import random

# MongoDB connection string with increased timeout settings
mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject?socketTimeoutMS=600000&connectTimeoutMS=600000"

# Create a MongoDB client with connection pooling
mongo_client = MongoClient(mongodb_connection_string, maxPoolSize=100)

# Access the specific database
mongo_db = mongo_client["mo9695_DBProject"]
products_collection = mongo_db['products']
orders_collection = mongo_db['orders']

# Function to generate review data
def generate_review(product_id, customer_id, order_id):
    review_id = ObjectId()
    score = random.randint(1, 5)  # Random score between 1 and 5

    if score == 5:
        title = "Excellent"
        content = "This product is amazing!"
    elif score == 4:
        title = "Very Good"
        content = "Very satisfied with the quality."
    elif score == 3:
        title = "Good"
        content = "Good value for money."
    elif score == 2:
        title = "Average"
        content = "Not as expected."
    else:
        title = "Poor"
        content = "Would not recommend."

    review_date = datetime.datetime.now()

    review = {
        "_id": review_id,
        "product_id": product_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "score": score,  # Ensure score is an integer
        "title": title,
        "content": content,
        "created_at": review_date
    }

    return review

# Function to embed reviews into the products collection
def embed_reviews_into_products(batch_size=100):
    # Fetch all product IDs
    products = list(products_collection.find({}, {"_id": 1}))
    
    # Fetch all order IDs
    orders = list(orders_collection.find({}, {"_id": 1}))

    if not products:
        raise ValueError("No products found in the database")
    
    if not orders:
        raise ValueError("No orders found in the database")

    for i in range(0, len(products), batch_size):
        batch = products[i:i+batch_size]
        updates = []
        for product in batch:
            product_id = product["_id"]
            customer_id = str(ObjectId())  # Simulating customer IDs as new ObjectIds

            # Generate a random number of reviews for each product
            num_reviews = random.randint(1, 5)

            # Randomly select an order_id for each review
            reviews = [generate_review(product_id, customer_id, random.choice(orders)["_id"]) for _ in range(num_reviews)]

            updates.append(UpdateOne(
                {"_id": product_id},
                {"$push": {"order_reviews": {"$each": reviews}}}
            ))

        # Perform bulk write for the current batch
        products_collection.bulk_write(updates)
        print(f"Processed batch {i // batch_size + 1} / {len(products) // batch_size + 1}")

    print("Reviews embedded into products successfully")

# Run the seeder
embed_reviews_into_products()
