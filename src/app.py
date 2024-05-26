from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Parse the database URL
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        
        if user:
            if user['seller_id']:
                session['seller_id'] = user['seller_id']
                return redirect(url_for('dashboard'))
            elif user['customer_id']:
                session['customer_id'] = user['customer_id']
                return redirect(url_for('shop'))
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        geolocation_id = request.form['geolocation_id']  # Assume geolocation ID is selected or provided
        
        cursor = db.cursor()
        
        if user_type == 'seller':
            cursor.execute("INSERT INTO sellers (geolocation_id) VALUES (%s)", (geolocation_id,))
            seller_id = cursor.lastrowid
            cursor.execute("INSERT INTO users (username, password, seller_id) VALUES (%s, %s, %s)", (username, password, seller_id))
        elif user_type == 'customer':
            cursor.execute("INSERT INTO customers (geolocation_id) VALUES (%s)", (geolocation_id,))
            customer_id = cursor.lastrowid
            cursor.execute("INSERT INTO users (username, password, customer_id) VALUES (%s, %s, %s)", (username, password, customer_id))
        
        db.commit()
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'seller_id' not in session:
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM products WHERE seller_id = %s", (seller_id,))
    products = cursor.fetchall()
    
    cursor.execute("SELECT r.*, p.product_category_name FROM order_reviews r JOIN order_items oi ON r.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.seller_id = %s", (seller_id,))
    reviews = cursor.fetchall()
    
    return render_template('dashboard.html', products=products, reviews=reviews)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'seller_id' not in session:
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        name_length = request.form['name_length']
        description_length = request.form['description_length']
        photos_qty = request.form['photos_qty']
        weight_g = request.form['weight_g']
        length_cm = request.form['length_cm']
        height_cm = request.form['height_cm']
        width_cm = request.form['width_cm']
        
        cursor.execute("""
            UPDATE products 
            SET product_name_length = %s, product_description_length = %s, product_photos_qty = %s, 
                product_weight_g = %s, product_length_cm = %s, product_height_cm = %s, product_width_cm = %s 
            WHERE product_id = %s AND seller_id = %s
        """, (name_length, description_length, photos_qty, weight_g, length_cm, height_cm, width_cm, product_id, seller_id))
        db.commit()
        
        return redirect(url_for('dashboard'))
    
    cursor.execute("SELECT * FROM products WHERE product_id = %s AND seller_id = %s", (product_id, seller_id))
    product = cursor.fetchone()
    
    return render_template('edit_product.html', product=product)

@app.route('/shop')
def shop():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    
    return render_template('shop.html', products=products)

if __name__ == '__main__':
    app.run(debug=True)
