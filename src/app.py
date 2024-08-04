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
    geolocation_data = []

    try:
        query = """
            SELECT country, city
            FROM geolocation
            ORDER BY country ASC, city ASC
        """
        data = execute_timed_query(db_session, query).fetchall()
        geolocation_data = [(location.country, location.city) for location in data]
    
    except Exception as e:
        return render_template('register.html', error=f"An error occurred while fetching geolocation data: {str(e)}", geolocation_data=geolocation_data)

    if request.method == 'POST':
        try:
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            user_type = request.form['user_type']
            
            result = execute_timed_query(db_session, "SELECT * FROM user WHERE username = :username", {'username': username})
            user = result.fetchone()
            
            if user:
                user_dict = {key: value for key, value in zip(result.keys(), user)}
                if user_type == 'seller' and user_dict.get('seller_id_fk'):
                    return render_template('register.html', error="User is already registered as a seller.", geolocation_data=geolocation_data)
                elif user_type == 'customer' and user_dict.get('customer_id_fk'):
                    return render_template('register.html', error="User is already registered as a customer.", geolocation_data=geolocation_data)
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
            return render_template('register.html', error=f"Missing form field: {e}", geolocation_data=geolocation_data)
        except Exception as e:
            return render_template('register.html', error=f"An error occurred: {str(e)}", geolocation_data=geolocation_data)
    
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

    categories = mongo_db.products.distinct("category")

    return render_template('add_product.html', categories=categories)

@app.route('/view_sales')
@role_required(role='seller')
def view_sales():
    seller_id = int(session['seller_id'])  # Ensure seller_id is an integer

    pipeline = [
            {"$unwind": "$order_items"},
            {"$project": {
                "order_items": 1,
                "product_id": "$order_items.product_id"
            }},
            {"$lookup": {
                "from": "products",
                "localField": "order_items.product_id",
                "foreignField": "_id",
                "as": "product_info"
            }},
            {"$unwind": "$product_info"},
            {"$match": {"product_info.seller_id": seller_id}},
            {"$group": {
                "_id": "$order_items.product_id",
                "name": {"$first": "$product_info.name"},
                "image_link": {"$first": "$product_info.image_link"},
                "sales_count": {"$sum": "$order_items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$order_items.quantity", "$order_items.price"]}}
            }},
            {"$sort": {"_id": 1}}
        ]
    
    sales_data = list(mongo_db.orders.aggregate(pipeline))
    
    for item in sales_data:
            item['_id'] = str(item['_id'])
    # convert the id from object id to str
    
    return render_template('view_sales.html', sales_data=sales_data)
    
@app.route('/view_product_sales/<product_id>')
@role_required(role='seller')
def view_product_sales(product_id):
    seller_id = int(session['seller_id'])  # Ensure seller_id is an integer

    try:
        # Step 1: MongoDB Aggregation Pipeline
        pipeline = [
            {"$unwind": "$order_items"},
            {"$match": {
                "order_items.product_id": ObjectId(product_id),
                "order_items.seller_id": seller_id
            }},
            {"$project": {
                "order_id": "$_id",
                "customer_id_fk": 1,
                "purchased_at": "$payment.purchased_at",
                "reviews": 1
            }},
            {"$unwind": {
                "path": "$reviews",
                "preserveNullAndEmptyArrays": True
            }},
            {"$project": {
                "order_id": 1,
                "purchased_at": 1,
                "customer_id_fk": 1,
                "has_review": {"$cond": [{"$gt": ["$reviews", None]}, True, False]}
            }}
        ]
        
        # Execute the aggregation pipeline
        product_sales = list(mongo_db.orders.aggregate(pipeline))

        # Step 2: Extract unique customer_id_fk values
        customer_ids = list(set(sale['customer_id_fk'] for sale in product_sales))

        customer_data = {}
        if customer_ids:
            # Step 3: Query SQL for Customer Usernames
            for customer_id in customer_ids:
                result = execute_timed_query(db_session, 
                                             "SELECT username FROM user WHERE customer_id_fk = :customer_id_fk", 
                                             {'customer_id_fk': customer_id})
                user = result.fetchone()
                print(user.username)
                if user:
                    customer_data[customer_id] = user.username

            # Step 4: Merge the SQL data with MongoDB data
            for sale in product_sales:
                sale['_id'] = str(sale['_id'])
                sale['order_id'] = str(sale['order_id'])
                sale['customer_username'] = customer_data.get(sale['customer_id_fk'], 'Unknown')
        
        # Render the results to the template
        return render_template('product_sales.html', product_sales=product_sales, has_sales=len(product_sales) > 0, product_id=product_id)

    except Exception as e:
        # Handle any errors that occur during the aggregation process
        return f"An error occurred: {str(e)}"

@app.route('/view_order_review_seller/<order_id>')
@role_required(role='seller')
def view_order_review_seller(order_id):
    try:
        # Find the order document by order_id
        order = mongo_db.orders.find_one({"_id": ObjectId(order_id)}, {"order_items": 1, "reviews": 1})

        if order:
            # Extract the relevant order item and review
            order_items = order.get('order_items', [])
            reviews = order.get('reviews', [])
            
            # Assuming there's a single review per order
            order_item = order_items[0] if order_items else None
            order_review = reviews[0] if reviews else None

            # Add the order_id to the review
            if order_review:
                order_review['order_id_fk'] = order_id

            # Add product_id_fk to order_item
            if order_item:
                order_item['product_id_fk'] = str(order_item['product_id'])

            return render_template('view_order_review_seller.html', order_review=order_review, order_item=order_item)
        else:
            return "Order not found."

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

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    price_min = request.args.get('price_min', '')
    price_max = request.args.get('price_max', '')
    sort_by = request.args.get('sort_by', '')

    print("Test statement here ----------")
    print(f"price_min: {price_min}, price_max: {price_max}")

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if category:
        query["category"] = category
    if price_min:
        query["price"] = {"$gte": float(price_min)}
    if price_max:
        query["price"] = query.get("price", {})
        query["price"]["$lte"] = float(price_max)

    print("Constructed query:", query)  # Debug statement

    sort_criteria = []
    if sort_by:
        if sort_by == 'price_asc':
            sort_criteria.append(("price", 1))
        elif sort_by == 'price_desc':
            sort_criteria.append(("price", -1))
        elif sort_by == 'name_asc':
            sort_criteria.append(("name", 1))
        elif sort_by == 'name_desc':
            sort_criteria.append(("name", -1))

    total_products = mongo_db.products.count_documents(query)
    total_pages = ceil(total_products / per_page)

    if sort_criteria:
        products = list(mongo_db.products.find(query).sort(sort_criteria).skip((page - 1) * per_page).limit(per_page))
    else:
        products = list(mongo_db.products.find(query).skip((page - 1) * per_page).limit(per_page))

    print("Found products:", products)  # Debug statement
    categories = mongo_db.products.distinct("category")

    return render_template('shop.html',
                           products=products,
                           categories=categories,
                           user_role=user_role,
                           page=page,
                           total_pages=total_pages,
                           search=search,
                           category=category,
                           price_min=price_min,
                           price_max=price_max,
                           sort_by=sort_by)

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
    categories = mongo_db.products.distinct("category")
    return render_template('edit_product.html', product=product, categories=categories)

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
                "total_price": {"$multiply": [{"$toDouble": "$product.price"}, {"$toInt": "$products.quantity"}]},  # Ensure multiplication is between numeric types
                "seller_id": "$product.seller_id"  # Include seller_id
            }}
        ]))

        total_amount = sum(item['total_price'] for item in cart_items)
        for item in cart_items:
            order_items.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "name": item["name"],  # Include product name
                "price": item["price"],  # Include product price
                "seller_id": item["seller_id"]  # Include seller_id
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

    # Ensure payment_type_id is a valid ObjectId
    if not payment_type_id or not ObjectId.is_valid(payment_type_id):
        flash("Invalid payment type ID", "error")
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

    return redirect(url_for('shop'))


# @app.route('/view_orders')
# @role_required(role='customer')
# def view_orders():
#     customer_id = session.get('customer_id')

#     if not customer_id:
#         flash('Customer ID is missing', 'error')
#         return redirect(url_for('shop'))

#     try:
#         orders = list(mongo_db.orders.aggregate([
#             {"$match": {"customer_id_fk": customer_id}},
#             {"$project": {
#                 "id": "$_id",
#                 "purchased_at": "$payment.purchased_at",
#                 "order_status": 1,
#                 "payment_value": {"$ifNull": ["$payment.payment_value", 0]},
#                 "has_review": {"$cond": [{"$gt": [{"$size": {"$ifNull": ["$reviews", []]}}, 0]}, True, False]},
#                 "reviews": 1
#             }}
#         ]))
        
#         print(orders)

#         return render_template('orders.html', orders=orders)
#     except Exception as e:
#         print(f"Error in view_orders: {e}")
#         return f"An error occurred: {str(e)}"
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
                "from": "products",
                "let": {"order_id": "$_id"},
                "pipeline": [
                    {"$unwind": "$order_reviews"},
                    {"$match": {"$expr": {"$eq": ["$order_reviews.order_id", "$$order_id"]}}}
                ],
                "as": "product_reviews"
            }},
            {"$project": {
                "id": "$_id",
                "purchased_at": "$payment.purchased_at",
                "order_status": 1,
                "payment_value": {"$ifNull": ["$payment.payment_value", 0]},
                "has_review": {"$cond": [{"$gt": [{"$size": {"$ifNull": ["$product_reviews", []]}}, 0]}, True, False]},
                "reviews": "$product_reviews.order_reviews"
            }}
        ]))

        print(orders)

        return render_template('orders.html', orders=orders)
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

# @app.route('/view_order_review_customer/<order_id>')
# @role_required(role='customer')
# def view_order_review(order_id):
#     order = mongo_db.orders.find_one({"_id": ObjectId(order_id)}, {"reviews": 1})
#     if not order or 'reviews' not in order:
#         return "No reviews found", 404

#     return render_template('view_order_review_customer.html', reviews=order['reviews'])

@app.route('/view_order_review_customer/<order_id>')
@role_required(role='customer')
def view_order_review(order_id):
    # Search for a product that contains the order_id in its order_reviews array
    product = mongo_db.products.find_one({"order_reviews.order_id": ObjectId(order_id)}, {"order_reviews.$": 1})
    
    if not product or 'order_reviews' not in product:
        return "No reviews found", 404

    reviews = product['order_reviews']
    return render_template('view_order_review_customer.html', reviews=reviews)



# @app.route('/write_order_review/<order_id>', methods=['GET', 'POST'])
# @role_required(role='customer')
# def write_order_review(order_id):
#     if request.method == 'POST':
#         score = request.form['score']
#         title = request.form['title']
#         content = request.form['content']
#         created_at = datetime.now()

#         review = {
#             "score": float(score),  # Ensure score is a float
#             "title": title,
#             "content": content,
#             "created_at": created_at
#         }
#         mongo_db.orders.update_one(
#             {"_id": ObjectId(order_id)},
#             {"$push": {"reviews": review}}
#         )

#         return redirect(url_for('view_orders'))
#     else:
#         return render_template('write_order_review.html', order_id=order_id)
@app.route('/write_order_review/<order_id>', methods=['GET', 'POST'])
@role_required(role='customer')
def write_order_review(order_id):
    if request.method == 'POST':
        score = request.form['score']
        title = request.form['title']
        content = request.form['content']
        created_at = datetime.now()
        customer_id = session['customer_id']  # Assuming you store the customer ID in session

        # Fetch the order to get product_id
        order = mongo_db.orders.find_one({"_id": ObjectId(order_id)})

        if not order:
            return "Order not found", 404

        # Assuming each order has one product in order_items
        product_id = order['order_items'][0]['product_id']

        review = {
            "_id": ObjectId(),
            "product_id": product_id,
            "order_id": ObjectId(order_id),
            "customer_id": customer_id,
            "score": int(score),  # Ensure score is a float
            "title": title,
            "content": content,
            "created_at": created_at
        }

        mongo_db.products.update_one(
            {"_id": product_id},
            {"$push": {"order_reviews": review}}
        )

        return redirect(url_for('view_orders'))
    else:
        return render_template('write_order_review.html', order_id=order_id)

@app.route('/sales_report')
@role_required(role='seller')
@query_timer
def sales_report():
    seller_id = session['seller_id']

    pipeline = [
        {"$unwind": "$order_items"},
        {"$match": {"order_items.seller_id": seller_id}},
        {"$group": {
            "_id": {
                "product_id": "$order_items.product_id",
                "product_name": "$order_items.name",
                "sale_month": {"$substr": ["$payment.purchased_at", 0, 7]}
            },
            "total_quantity_sold": {"$sum": "$order_items.quantity"},
            "total_revenue": {"$sum": {"$multiply": ["$order_items.quantity", "$order_items.price"]}}
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
    page = int(request.args.get('page', 1))
    per_page = 10

    try:
        pipeline = [
            {"$match": {"seller_id": seller_id}},  # Match products by seller_id
            {"$unwind": "$order_reviews"},  # Unwind the order_reviews array
            {"$group": {
                "_id": {
                    "product_id": "$_id",
                    "product_name": "$name"
                },
                "review_count": {"$sum": 1},
                "average_score": {"$avg": "$order_reviews.score"},  # Ensure score is a double
                "reviews": {"$push": "$order_reviews"}
            }},
            {"$sort": {"average_score": -1, "review_count": -1}},
            {"$skip": (page - 1) * per_page},
            {"$limit": per_page}
        ]

        product_reviews = list(mongo_db.products.aggregate(pipeline))

        total_reviews_pipeline = [
            {"$match": {"seller_id": seller_id}},
            {"$unwind": "$order_reviews"},
            {"$count": "total_reviews"}
        ]
        total_reviews_result = list(mongo_db.products.aggregate(total_reviews_pipeline))
        total_reviews = total_reviews_result[0]["total_reviews"] if total_reviews_result else 0
        total_pages = (total_reviews + per_page - 1) // per_page

        # Convert ObjectId to string for template rendering
        for review in product_reviews:
            review['_id']['product_id'] = str(review['_id']['product_id'])

        return render_template('product_reviews.html', product_reviews=product_reviews, page=page, total_pages=total_pages)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while fetching product reviews", 500


def signal_handler(signal, frame):
    print('Received shutdown signal. Cleaning up...')
    # Perform necessary cleanup here
    os._exit(0)

if __name__ == '__main__':
    if is_running_from_reloader():
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    app.run(debug=True)
