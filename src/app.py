from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine, mongo_db
from werkzeug.utils import secure_filename
import base64
from datetime import datetime
import time
import functools
import psutil
import logging
from bson import ObjectId
import signal
import os
from werkzeug.serving import is_running_from_reloader
from math import ceil

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create a configured "Session" class
Session = sessionmaker(bind=engine)
# Create a Session
db_session = Session()

def execute_timed_query(db_session, query, params=None):
    if params is None:
        params = {}

    print(f"Executing query: {query}")
    start_time = time.time()
    start_cpu = psutil.cpu_percent(interval=None)
    start_memory = psutil.virtual_memory().used
    result = db_session.execute(text(query), params)
    query_time = time.time() - start_time
    end_cpu = psutil.cpu_percent(interval=None)
    end_memory = psutil.virtual_memory().used

    cpu_usage = end_cpu - start_cpu
    memory_usage = end_memory - start_memory
    print(f"Query time: {query_time:.4f} seconds")
    print(f"CPU usage: {cpu_usage:.2f}%")
    print(f"Memory usage: {memory_usage / 1024:.2f} KB")
    
    return result

def fetch_all(db_session, query, params=None):
    if params is None:
        params = {}

    try:
        result = db_session.execute(text(query), params).fetchall()
        return result
    except Exception as e:
        raise e

def fetch_one(db_session, query, params=None):
    if params is None:
        params = {}

    try:
        result = db_session.execute(text(query), params).fetchone()
        return result
    except Exception as e:
        raise e

def query_timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_cpu = psutil.cpu_percent(interval=None)
        start_memory = psutil.virtual_memory().used
        result = func(*args, **kwargs)
        end_time = time.time()
        end_cpu = psutil.cpu_percent(interval=None)
        end_memory = psutil.virtual_memory().used
        execution_time = end_time - start_time
        cpu_usage = end_cpu - start_cpu
        memory_usage = end_memory - start_memory
        print(f"Query '{func.__name__}' executed in {execution_time:.4f} seconds")
        print(f"CPU usage: {cpu_usage:.2f}%")
        print(f"Memory usage: {memory_usage / 1024:.2f} KB")
        return result
    return wrapper

def update_total_amount(session_id):
    shopping_session = mongo_db.shopping_sessions.find_one({"_id": ObjectId(session_id)})
    if not shopping_session:
        print(f"Shopping session not found: {session_id}")
        return

    total_amount = 0
    for item in shopping_session.get('products', []):
        product = mongo_db.products.find_one({"_id": item['product_id']})
        try:
            quantity = int(item['quantity'])
            price = float(product['price'])
            print(f"Item quantity: {quantity}, Item price: {price}")
            total_amount += quantity * price
        except ValueError as e:
            print(f"ValueError: {e}")
            continue
        except TypeError as e:
            print(f"TypeError: {e}")
            continue

    print(f"Total amount: {total_amount}")
    mongo_db.shopping_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"total_amount": total_amount}})

def role_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'seller_id' not in session and 'customer_id' not in session:
                return redirect(url_for('login'))

            if role == 'seller' and ('seller_id' not in session or session.get('role') != 'seller'):
                return redirect(url_for('login', next=request.url))
            elif role == 'customer' and ('customer_id' not in session or session.get('role') != 'customer'):
                return redirect(url_for('login', next=request.url))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def order_has_review(order_id):
    review_count = mongo_db.order_reviews.count_documents({"order_id": order_id})
    return review_count > 0

@app.route('/')
@role_required()
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        result = execute_timed_query(db_session, "SELECT * FROM user WHERE username = :username", {'username': username})
        user = result.fetchone()
        
        if user:
            user_dict = {key: value for key, value in zip(result.keys(), user)}
            if check_password_hash(user_dict['password'], password):
                session['username'] = username
                session['logged_in'] = True
                
                if role == 'seller':
                    if user_dict['seller_id_fk']:
                        session['seller_id'] = user_dict['seller_id_fk']
                        session['role'] = 'seller'
                        return redirect(url_for('dashboard'))
                    else:
                        flash("No seller account linked to this user.")
                        return redirect(url_for('login'))
                
                elif role == 'customer':
                    if user_dict['customer_id_fk']:
                        session['customer_id'] = user_dict['customer_id_fk']
                        session['role'] = 'customer'
                        return redirect(url_for('shop'))
                    else:
                        flash("No customer account linked to this user.")
                        return redirect(url_for('login'))
            else:
                flash("Invalid credentials")
                return redirect(url_for('login'))
        else:
            flash("Invalid credentials")
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('seller_id', None)
    session.pop('customer_id', None)
    session.pop('role', None)
    session['logged_in'] = False
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            user_type = request.form['user_type']
            
            result = execute_timed_query(db_session, "SELECT * FROM user WHERE username = :username", {'username': username})
            user = result.fetchone()
            
            if user:
                user_dict = {key: value for key, value in zip(result.keys(), user)}
                if user_type == 'seller' and user_dict['seller_id_fk']:
                    return render_template('register.html', error="User is already registered as a seller.")
                elif user_type == 'customer' and user_dict['customer_id_fk']:
                    return render_template('register.html', error="User is already registered as a customer.")
                else:
                    geolocation_id = execute_timed_query(db_session, "SELECT id FROM geolocation WHERE country = :country AND city = :city", {'country': request.form['user_country'], 'city': request.form['user_city']}).scalar()

                    if user_type == 'seller':
                        execute_timed_query(db_session, "INSERT INTO seller (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                        seller_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        execute_timed_query(db_session, "UPDATE user SET seller_id_fk = :seller_id WHERE username = :username", {'seller_id': seller_id, 'username': username})
                    elif user_type == 'customer':
                        execute_timed_query(db_session, "INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                        customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        execute_timed_query(db_session, "UPDATE user SET customer_id_fk = :customer_id WHERE username = :username", {'customer_id': customer_id, 'username': username})

                    db_session.commit()
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
            else:
                geolocation_id = execute_timed_query(db_session, "SELECT id FROM geolocation WHERE country = :country AND city = :city", {'country': request.form['user_country'], 'city': request.form['user_city']}).scalar()

                if user_type == 'seller':
                    execute_timed_query(db_session, "INSERT INTO seller (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                    seller_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    execute_timed_query(db_session, "INSERT INTO user (username, password, seller_id_fk) VALUES (:username, :password, :seller_id)", {'username': username, 'password': password, 'seller_id': seller_id})
                elif user_type == 'customer':
                    execute_timed_query(db_session, "INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                    customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    execute_timed_query(db_session, "INSERT INTO user (username, password, customer_id_fk) VALUES (:username, :password, :customer_id)", {'username': username, 'password': password, 'customer_id': customer_id})

                db_session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
        except KeyError as e:
            return render_template('register.html', error=f"Missing form field: {e}")
    
    geolocation_data = None
    
    try:
        query = """
            SELECT country, city
            FROM geolocation
            ORDER BY country ASC, city ASC
        """
        data = execute_timed_query(db_session, query).fetchall()
        geolocation_data = [(location.country, location.city) for location in data]
    
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
    return render_template('register.html', geolocation_data=geolocation_data)

@app.route('/dashboard')
@role_required(role='seller')
def dashboard():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    
    try:
        products = list(mongo_db.products.find({"seller_id": seller_id}))
        return render_template('dashboard.html', products=products)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

@app.route('/add_product', methods=['GET', 'POST'])
@role_required(role='seller')
def add_product():
    
    seller_id = session['seller_id']
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        weight = request.form['weight']
        length = request.form['length']
        height = request.form['height']
        width = request.form['width']
        price = request.form['price']
        image_url = request.form['image_url']  # Assuming you're now submitting an image URL

        try:
            product = {
                "name": name,
                "description": description,
                "category": category,
                "weight": weight,
                "length": length,
                "height": height,
                "width": width,
                "price": price,
                "image_link": image_url,
                "seller_id": seller_id
            }
            mongo_db.products.insert_one(product)
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            return f"An error occurred: {str(e)}"

    return render_template('add_product.html')

@app.route('/view_sales')
@role_required(role='seller')
def view_sales():
    seller_id = session['seller_id']

    try:
        pipeline = [
            {"$match": {"seller_id": seller_id}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": {"product_id": "$items.product_id", "name": "$items.name"},
                "sales_count": {"$sum": "$items.quantity"}
            }},
            {"$sort": {"_id.product_id": 1}}
        ]
        sales_data = list(mongo_db.orders.aggregate(pipeline))

        return render_template('view_sales.html', sales_data=sales_data)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/view_product_sales/<int:product_id>')
@role_required(role='seller')
def view_product_sales(product_id):

    seller_id = session['seller_id']

    try:
        pipeline = [
            {"$match": {"seller_id": seller_id, "items.product_id": product_id}},
            {"$unwind": "$items"},
            {"$match": {"items.product_id": product_id}},
            {"$lookup": {
                "from": "users",
                "localField": "customer_id",
                "foreignField": "customer_id_fk",
                "as": "customer"
            }},
            {"$unwind": "$customer"},
            {"$lookup": {
                "from": "order_reviews",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "reviews"
            }},
            {"$unwind": {
                "path": "$reviews",
                "preserveNullAndEmptyArrays": True
            }},
            {"$project": {
                "order_id": 1,
                "purchased_at": 1,
                "customer_username": "$customer.username",
                "has_review": {"$cond": [{"$gt": ["$reviews", None]}, True, False]}
            }}
        ]
        product_sales = list(mongo_db.orders.aggregate(pipeline))
        has_sales = len(product_sales) > 0

        return render_template('product_sales.html', product_sales=product_sales, has_sales=has_sales)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/view_order_review_seller/<int:order_id>')
@role_required(role='seller')
def view_order_review_seller(order_id):
    
    try:
        order_review = mongo_db.order_reviews.find_one({"order_id": order_id})
        order_item = mongo_db.orders.find_one({"items.order_id": order_id}, {"items.$": 1})

        return render_template('view_order_review_seller.html', order_review=order_review, order_item=order_item)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/shop', methods=['GET', 'POST'])
@role_required()
def shop():

    user_role = session.get('role')

    if user_role == 'customer':
        customer_id = session.get('customer_id')
        if not customer_id:
            return redirect(url_for('login'))

        active_session = mongo_db.shopping_sessions.find_one({"customer_id_fk": customer_id})

        if not active_session:
            active_session = {
                "customer_id_fk": customer_id,
                "created_at": datetime.now(),
                "total_amount": 0
            }
            mongo_db.shopping_sessions.insert_one(active_session)
            active_session = mongo_db.shopping_sessions.find_one({"customer_id_fk": customer_id})

        session['shopping_session_id'] = str(active_session["_id"])

    elif user_role == 'seller':
        seller_id = session.get('seller_id')
        if not seller_id:
            return redirect(url_for('login'))

    search = request.form.get('search', '')
    category = request.form.get('category', '')
    price_min = request.form.get('price_min', '')
    price_max = request.form.get('price_max', '')
    sort_by = request.form.get('sort_by', '')

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = {"name": {"$regex": search, "$options": "i"}}
    if category:
        query["category"] = category
    if price_min:
        query["price"] = {"$gte": float(price_min)}
    if price_max:
        query["price"] = {"$lte": float(price_max)}

    sort_criteria = None
    if sort_by:
        if sort_by == 'price_asc':
            sort_criteria = [("price", 1)]
        elif sort_by == 'price_desc':
            sort_criteria = [("price", -1)]
        elif sort_by == 'name_asc':
            sort_criteria = [("name", 1)]
        elif sort_by == 'name_desc':
            sort_criteria = [("name", -1)]

    total_products = mongo_db.products.count_documents(query)
    total_pages = ceil(total_products / per_page)

    products = list(mongo_db.products.find(query, sort=sort_criteria).skip((page-1)*per_page).limit(per_page))

    categories = mongo_db.products.distinct("category")

    return render_template('shop.html', 
                           products=products, 
                           categories=categories, 
                           user_role=user_role,
                           page=page,
                           total_pages=total_pages)

@app.route('/product/<product_id>')
def product(product_id):
    product = mongo_db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        return "Product not found", 404
    return render_template('product.html', product=product)


@app.route('/edit_product/<product_id>', methods=['GET', 'POST'])
@role_required(role='seller')
def edit_product(product_id):

    seller_id = session['seller_id']
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        weight = request.form['weight']
        length = request.form['length']
        height = request.form['height']
        width = request.form['width']
        
        mongo_db.products.update_one(
            {"_id": ObjectId(product_id), "seller_id": seller_id},
            {"$set": {
                "name": name,
                "description": description,
                "weight": weight,
                "length": length,
                "height": height,
                "width": width
            }}
        )
        
        return redirect(url_for('dashboard'))
    
    product = mongo_db.products.find_one({"_id": ObjectId(product_id), "seller_id": seller_id})
    return render_template('edit_product.html', product=product)

@app.route('/order/<order_id>/payment')
@role_required(role='customer')
def order_payment(order_id):
    order = mongo_db.orders.find_one({"_id": ObjectId(order_id)}, {"payment": 1, "_id": 0})

    if not order or 'payment' not in order:
        return "Payment details not found", 404

    order_payment = order['payment']

    return render_template('order_payment.html', order_payment=order_payment)


@app.route('/order/<order_id>/review')
@role_required(role='customer')
def order_review(order_id):
    order_review = mongo_db.order_reviews.find({"order_id_fk": ObjectId(order_id)}).all()
    return render_template('order_review.html', order_review=order_review)

@app.route('/add_to_cart/<product_id>', methods=['POST'])
@role_required(role='customer')
def add_to_cart(product_id):

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    quantity = request.form.get('quantity', 1)
    try:
        quantity = int(quantity)
        print(f"Quantity to add: {quantity}")
    except ValueError:
        print(f"Invalid quantity value: {quantity}")
        return "Invalid quantity value", 400

    cart_item = mongo_db.shopping_sessions.find_one(
        {"_id": ObjectId(shopping_session_id), "products.product_id": ObjectId(product_id)},
        {"products.$": 1}
    )

    if cart_item:
        current_quantity = cart_item['products'][0]['quantity']
        try:
            current_quantity = int(current_quantity)
            print(f"Current quantity in cart: {current_quantity}")
        except ValueError:
            print(f"Invalid current quantity value: {current_quantity}")
            return "Invalid quantity in cart item", 500

        new_quantity = current_quantity + quantity
        print(f"New quantity: {new_quantity}")
        mongo_db.shopping_sessions.update_one(
            {"_id": ObjectId(shopping_session_id), "products.product_id": ObjectId(product_id)},
            {"$set": {"products.$.quantity": new_quantity}}
        )
    else:
        cart_item = {
            "product_id": ObjectId(product_id),
            "quantity": quantity
        }
        mongo_db.shopping_sessions.update_one(
            {"_id": ObjectId(shopping_session_id)},
            {"$push": {"products": cart_item}}
        )

    update_total_amount(ObjectId(shopping_session_id))

    return redirect(url_for('view_cart'))


@app.route('/update_cart/<product_id>', methods=['POST'])
@role_required(role='customer')
def update_cart(product_id):
    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    quantity = request.form.get('quantity', 1)
    try:
        quantity = int(quantity)
        print(f"Updated quantity: {quantity}")
    except ValueError:
        print(f"Invalid quantity value: {quantity}")
        return "Invalid quantity value", 400

    if quantity < 1:
        quantity = 1

    mongo_db.shopping_sessions.update_one(
        {"_id": ObjectId(shopping_session_id), "products.product_id": ObjectId(product_id)},
        {"$set": {"products.$.quantity": quantity}}
    )

    update_total_amount(ObjectId(shopping_session_id))

    flash('Cart updated successfully', 'success')
    return redirect(url_for('view_cart'))


@app.route('/remove_from_cart/<product_id>', methods=['POST'])
@role_required(role='customer')
def remove_from_cart(product_id):
    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    mongo_db.shopping_sessions.update_one(
        {"_id": ObjectId(shopping_session_id)},
        {"$pull": {"products": {"product_id": ObjectId(product_id)}}}
    )

    update_total_amount(ObjectId(shopping_session_id))

    return redirect(url_for('view_cart'))


@app.route('/cart')
@role_required(role='customer')
def view_cart():
    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    cart_items = list(mongo_db.shopping_sessions.aggregate([
        {"$match": {"_id": ObjectId(shopping_session_id)}},
        {"$unwind": "$products"},
        {"$lookup": {
            "from": "products",
            "localField": "products.product_id",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": "$product"},
        {"$project": {
            "product_id": "$product._id",
            "name": "$product.name",
            "price": {"$toDouble": "$product.price"},  # Ensure price is a double
            "quantity": {"$toInt": "$products.quantity"},  # Ensure quantity is an integer
            "total_price": {"$multiply": [{"$toDouble": "$product.price"}, {"$toInt": "$products.quantity"}]}  # Ensure multiplication is between numeric types
        }}
    ]))

    total_amount = mongo_db.shopping_sessions.find_one({"_id": ObjectId(shopping_session_id)})['total_amount']

    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

def ensure_payment_types():
    payment_types = ['Visa', 'Credit Card', 'Paynow']
    existing_payment_types = list(mongo_db.payment_types.find({}, {"payment_name": 1}))

    existing_payment_names = [ptype['payment_name'] for ptype in existing_payment_types]

    for payment_type in payment_types:
        if payment_type not in existing_payment_names:
            mongo_db.payment_types.insert_one({"payment_name": payment_type})

ensure_payment_types()

@app.route('/checkout', methods=['GET', 'POST'])
@role_required(role='customer')
def checkout():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    if request.method == 'POST':
        order_id = request.form['order_id']
        payment_type_id = request.form['payment_type_id']

        # Directly update the order document
        mongo_db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "order_status": "paid", 
                "payment.payment_type": payment_type_id,
                "payment.purchased_at": datetime.now()
            }}
        )

        return redirect(url_for('shop'))
    else:
        customer_id = session['customer_id']
        order_items = []
        total_payment_value = 0

        cart_items = list(mongo_db.shopping_sessions.aggregate([
            {"$match": {"_id": ObjectId(shopping_session_id)}},
            {"$unwind": "$products"},
            {"$lookup": {
                "from": "products",
                "localField": "products.product_id",
                "foreignField": "_id",
                "as": "product"
            }},
            {"$unwind": "$product"},
            {"$project": {
                "product_id": "$product._id",
                "name": "$product.name",
                "price": {"$toDouble": "$product.price"},  # Ensure price is a double
                "quantity": {"$toInt": "$products.quantity"},  # Ensure quantity is an integer
                "total_price": {"$multiply": [{"$toDouble": "$product.price"}, {"$toInt": "$products.quantity"}]}  # Ensure multiplication is between numeric types
            }}
        ]))

        total_amount = sum(item['total_price'] for item in cart_items)
        for item in cart_items:
            order_items.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"]
            })

        purchased_at = datetime.now()

        order = {
            "customer_id_fk": customer_id,
            "order_status": "unpaid",
            "payment": {
                "payment_type": "credit_card",  # This can be dynamically set based on user input
                "payment_installments": 1,
                "payment_value": round(total_amount, 2),
                "purchased_at": purchased_at
            },
            "order_items": order_items
        }
        result = mongo_db.orders.insert_one(order)
        order_id = result.inserted_id

        return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, order_id=order_id)


@app.route('/process_checkout', methods=['POST'])
@role_required(role='customer')
def process_checkout():
    order_id = request.form['order_id']
    total_amount = request.form['total_amount']
    return redirect(url_for('payment', order_id=order_id, total_amount=total_amount))

@app.route('/payment/<order_id>', methods=['GET', 'POST'])
@role_required(role='customer')
def payment(order_id):
    total_amount = request.args.get('total_amount')
    payment_types = list(mongo_db.payment_types.find({}))

    return render_template('payment.html', order_id=order_id, total_amount=total_amount, payment_types=payment_types)

@app.route('/process_payment/<order_id>', methods=['POST'])
@role_required(role='customer')
def process_payment(order_id):
    payment_type_id = request.form.get('payment_type_id')
    total_amount = request.form.get('total_amount')

    print(f"Received payment_type_id: {payment_type_id}")  # Debug statement
    print(f"Received total_amount: {total_amount}")  # Debug statement

    # Ensure payment_type_id is a valid ObjectId
    if not payment_type_id or not ObjectId.is_valid(payment_type_id):
        flash("Invalid payment type ID", "error")
        print("Invalid payment type ID")  # Debug statement
        return redirect(url_for('payment', order_id=order_id))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        flash("Shopping session not found", "error")
        return redirect(url_for('shop'))

    # Ensure total_amount is a valid float
    try:
        total_amount = float(total_amount)
    except ValueError:
        flash("Invalid total amount", "error")
        print("Invalid total amount")  # Debug statement
        return redirect(url_for('payment', order_id=order_id))

    approved_at = datetime.now()

    # Update the order document directly
    mongo_db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "order_status": "paid", 
            "payment.payment_type": payment_type_id,
            "payment.payment_value": total_amount,
            "payment.approved_at": approved_at
        }}
    )

    # Clear the shopping session
    mongo_db.shopping_sessions.update_one(
        {"_id": ObjectId(shopping_session_id)},
        {"$set": {"total_amount": 0, "products": []}}
    )

    print("Payment processed successfully")  # Debug statement

    return redirect(url_for('shop'))


@app.route('/view_orders')
@role_required(role='customer')
def view_orders():
    customer_id = session.get('customer_id')

    if not customer_id:
        flash('Customer ID is missing', 'error')
        return redirect(url_for('shop'))

    try:
        orders = list(mongo_db.orders.aggregate([
            {"$match": {"customer_id_fk": customer_id}},
            {"$lookup": {
                "from": "order_payments",
                "localField": "_id",
                "foreignField": "order_id_fk",
                "as": "payments"
            }},
            {"$unwind": {
                "path": "$payments",
                "preserveNullAndEmptyArrays": True
            }},
            {"$lookup": {
                "from": "order_reviews",
                "localField": "_id",
                "foreignField": "order_id_fk",
                "as": "reviews"
            }},
            {"$unwind": {
                "path": "$reviews",
                "preserveNullAndEmptyArrays": True
            }},
            {"$project": {
                "id": "$_id",
                "purchased_at": 1,
                "order_status": 1,
                "payment_value": {"$ifNull": ["$payments.payment_value", 0]},
                "has_review": {"$cond": [{"$gt": ["$reviews", None]}, True, False]},
                "score": {"$ifNull": ["$reviews.score", 0]},
                "title": {"$ifNull": ["$reviews.title", ""]},
                "content": {"$ifNull": ["$reviews.content", ""]}
            }}
        ]))

        return render_template('orders.html', orders=orders, order_has_review=order_has_review)
    except Exception as e:
        print(f"Error in view_orders: {e}")
        return f"An error occurred: {str(e)}"

@app.route('/view_order_detail/<order_id>')
@role_required(role='customer')
def view_order_detail(order_id):
    order = mongo_db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        return "Order not found", 404

    order_items = []
    for item in order.get("order_items", []):
        product = mongo_db.products.find_one({"_id": item["product_id"]})
        if product:
            order_items.append({
                "product_name": product["name"],
                "price": float(product["price"]),
                "quantity": int(item["quantity"]),
                "total_price": float(product["price"]) * int(item["quantity"])
            })

    return render_template('order_detail.html', order=order, order_items=order_items)


@app.route('/order_reviews/<order_id>')
@role_required(role='customer')
def order_reviews(order_id):
    order_reviews = list(mongo_db.order_reviews.find({"order_id_fk": ObjectId(order_id)}))
    return render_template('order_reviews.html', order_reviews=order_reviews)

@app.route('/view_order_review_customer/<order_id>')
@role_required(role='customer')
def view_order_review(order_id):
    order_review = mongo_db.order_reviews.find_one({"order_id_fk": ObjectId(order_id)})
    return render_template('view_order_review_customer.html', order_review=order_review)

@app.route('/write_order_review/<order_id>', methods=['GET', 'POST'])
@role_required(role='customer')
def write_order_review(order_id):
    if request.method == 'POST':
        score = request.form['score']
        title = request.form['title']
        content = request.form['content']
        created_at = datetime.now()

        order_review = {
            "order_id_fk": ObjectId(order_id),
            "score": {"$toDouble": score},  # Ensure score is a double
            "title": title,
            "content": content,
            "created_at": created_at
        }
        mongo_db.order_reviews.insert_one(order_review)

        return redirect(url_for('view_orders'))
    else:
        return render_template('write_order_review.html', order_id=order_id)

@app.route('/sales_report')
@role_required(role='seller')
@query_timer
def sales_report():
    seller_id = session['seller_id']

    pipeline = [
        {"$match": {"seller_id": seller_id}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": {
                "product_id": "$items.product_id",
                "product_name": "$items.name",
                "sale_month": {"$substr": ["$purchased_at", 0, 7]}
            },
            "total_quantity_sold": {"$sum": {"$toInt": "$items.quantity"}},  # Ensure quantity is an integer
            "total_revenue": {"$sum": {"$multiply": [{"$toInt": "$items.quantity"}, {"$toDouble": "$items.price"}]}}  # Ensure multiplication is between numeric types
        }},
        {"$sort": {"_id.product_id": 1, "_id.sale_month": 1}}
    ]

    sales_report = list(mongo_db.orders.aggregate(pipeline))
    return render_template('sales_report.html', sales_report=sales_report)

@app.route('/product_reviews')
@role_required(role='seller')
@query_timer
def product_reviews():
    seller_id = session['seller_id']

    pipeline = [
        {"$match": {"seller_id": seller_id}},
        {"$unwind": "$items"},
        {"$lookup": {
            "from": "order_reviews",
            "localField": "order_id",
            "foreignField": "order_id_fk",
            "as": "reviews"
        }},
        {"$unwind": {
            "path": "$reviews",
            "preserveNullAndEmptyArrays": True
        }},
        {"$group": {
            "_id": {
                "product_id": "$items.product_id",
                "product_name": "$items.name"
            },
            "review_count": {"$sum": {"$cond": [{"$gt": ["$reviews", None]}, 1, 0]}},
            "average_score": {"$avg": {"$toDouble": "$reviews.score"}}  # Ensure score is a double
        }},
        {"$sort": {"average_score": -1, "review_count": -1}}
    ]

    product_reviews = list(mongo_db.orders.aggregate(pipeline))
    return render_template('product_reviews.html', product_reviews=product_reviews)

def signal_handler(signal, frame):
    print('Received shutdown signal. Cleaning up...')
    # Perform necessary cleanup here
    os._exit(0)

if __name__ == '__main__':
    if is_running_from_reloader():
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    app.run(debug=True)
