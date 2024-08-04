import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
from database import mongo_db
import os
import random

# Exchange rate (as of 2023-07-23, 1 INR = 0.012 USD)
INR_TO_USD = 0.012

# Print current working directory and files
print("Current working directory:", os.getcwd())

# List available datasets
datasets_dir = 'amazon_datasets'
if not os.path.exists(datasets_dir):
    print(f"Error: '{datasets_dir}' directory not found.")
    exit()

available_datasets = [f for f in os.listdir(datasets_dir) if f.endswith('_amazon_database.csv')]

if not available_datasets:
    print(f"No dataset files found in '{datasets_dir}'. Make sure your CSV files end with '_amazon_database.csv'")
    exit()

print("Available datasets:")
for i, dataset in enumerate(available_datasets, 1):
    print(f"{i}. {dataset}")

# Prompt user to choose a dataset
while True:
    try:
        choice = int(input("Enter the number of the dataset you want to use: "))
        if 1 <= choice <= len(available_datasets):
            chosen_dataset = available_datasets[choice - 1]
            break
        else:
            print("Invalid choice. Please try again.")
    except ValueError:
        print("Please enter a valid number.")

# Load the chosen dataset
try:
    df = pd.read_csv(os.path.join(datasets_dir, chosen_dataset))
    print(f"CSV file '{chosen_dataset}' read successfully")
    print("Columns in the CSV file:", df.columns.tolist())
except Exception as e:
    print(f"An error occurred while reading the CSV file: {e}")
    exit()

# Clean and preprocess the data
df = df.dropna(subset=['name', 'image', 'discount_price'])

# Function to clean price and convert to USD
def clean_and_convert_price(price):
    price_inr = float(price.replace('₹', '').replace(',', ''))
    price_usd = round(price_inr * INR_TO_USD, 2)
    return str(price_usd)

# Rename and process columns
df = df.rename(columns={'discount_price': 'price', 'image': 'image_link'})
df['price'] = df['price'].apply(clean_and_convert_price)

# Set category based on the chosen dataset
category = chosen_dataset.split('_')[0].capitalize()
df['category'] = category
df['description'] = df['main_category']
df['weight'] = "0.03"
df['length'] = "0"
df['height'] = "0.01"
df['width'] = "0.01"

# Assign a random seller_id between 1 and 23
df['seller_id'] = [random.randint(1, 23) for _ in range(len(df))]

# Select final columns
df = df[['name', 'description', 'category', 'price', 'image_link', 'weight', 'length', 'height', 'width', 'seller_id']]

# Convert DataFrame to list of dictionaries
products = df.to_dict('records')

# Function to insert products into MongoDB
def insert_amazon_products(products):
    try:
        for idx, product in enumerate(products):
            product['_id'] = ObjectId()
            mongo_db.products.insert_one(product)
            print(f"Inserted document {idx + 1}: {product}")
        print(f"Inserted {len(products)} documents into the products collection")
    except Exception as e:
        print(f"An error occurred: {e}")

# Insert products and create indexes
insert_amazon_products(products)

def create_indexes():
    try:
        mongo_db.products.create_index("name")
        mongo_db.products.create_index("category")
        mongo_db.products.create_index("price")
        print("Indexes created successfully")
    except Exception as e:
        print(f"An error occurred while creating indexes: {e}")

create_indexes()    