import mysql.connector
from urllib.parse import urlparse

# Database configuration
db_url = "mysql://bacccc3deb3049:86d5cd2b@us-cluster-east-01.k8s.cleardb.net/heroku_a4ac16748985540?reconnect=true"
url = urlparse(db_url)
db_config = {
    'host': url.hostname,
    'user': url.username,
    'password': url.password,
    'database': url.path[1:],
    'port': url.port or 3306  # Default to 3306 if no port is specified
}

db = mysql.connector.connect(**db_config)
cursor = db.cursor()

# Fetch all product IDs
cursor.execute("SELECT product_id FROM products")
products = cursor.fetchall()

# Fetch all seller IDs
cursor.execute("SELECT seller_id FROM sellers")
sellers = cursor.fetchall()

# Distribute products among sellers
for i, product in enumerate(products):
    seller_id = sellers[i % len(sellers)][0]
    cursor.execute("UPDATE products SET seller_id = %s WHERE product_id = %s", (seller_id, product[0]))

db.commit()
cursor.close()
db.close()
