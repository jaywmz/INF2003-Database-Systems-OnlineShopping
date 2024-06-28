from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from werkzeug.utils import secure_filename
import base64
from datetime import datetime
import time
import functools
import psutil
import logging


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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def order_has_review(order_id):
    # Query to check if the order has a review
    review_count = db_session.execute(text("SELECT COUNT(*) FROM order_review WHERE order_id_fk = :order_id"),
                                      {'order_id': order_id}).scalar()
    return review_count > 0


@app.route('/')
@login_required
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
            password = generate_password_hash(request.form['password'])  # Hash the password
            user_type = request.form['user_type']
            
            # Check if the username already exists
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
                        execute_timed_query(db_session, "UPDATE user SET seller_id_fk = :seller_id WHERE username = :username",
                                           {'seller_id': seller_id, 'username': username})
                    elif user_type == 'customer':
                        execute_timed_query(db_session, "INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                        customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        execute_timed_query(db_session, "UPDATE user SET customer_id_fk = :customer_id WHERE username = :username",
                                           {'customer_id': customer_id, 'username': username})

                    db_session.commit()
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
            else:
                geolocation_id = execute_timed_query(db_session, "SELECT id FROM geolocation WHERE country = :country AND city = :city", {'country': request.form['user_country'], 'city': request.form['user_city']}).scalar()

                if user_type == 'seller':
                    execute_timed_query(db_session, "INSERT INTO seller (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                    seller_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    execute_timed_query(db_session, "INSERT INTO user (username, password, seller_id_fk) VALUES (:username, :password, :seller_id)",
                                       {'username': username, 'password': password, 'seller_id': seller_id})
                elif user_type == 'customer':
                    execute_timed_query(db_session, "INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)", {'geolocation_id': geolocation_id})
                    customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    execute_timed_query(db_session, "INSERT INTO user (username, password, customer_id_fk) VALUES (:username, :password, :customer_id)",
                                       {'username': username, 'password': password, 'customer_id': customer_id})

                db_session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
        except KeyError as e:
            return render_template('register.html', error=f"Missing form field: {e}")
    
    geolocation_data = None
    
    try:
        # Query to get the number of sales per product along with product details for the logged-in seller
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
@login_required
def dashboard():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    
    try:
        # Construct the SQL query with timing
        query = """
            SELECT p.*, pc.name as category_name, pi.image_link
            FROM product p
            JOIN product_category pc ON p.product_category_id_fk = pc.id
            JOIN product_image pi ON p.id = pi.product_id_fk
            WHERE p.seller_id_fk = :seller_id
        """
        
        # Execute the timed query
        products = execute_timed_query(db_session, query, {'seller_id': seller_id}).fetchall()
        
        return render_template('dashboard.html', products=products)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if 'seller_id' not in session:
        return redirect(url_for('login'))
    
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

        # Handle file upload
        image_file = request.files['image_file']
        if image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

            try:
                # Insert the product and link it to the seller
                query = """
                    INSERT INTO product (name, description, product_category_id_fk, price, weight, length, height, width, seller_id_fk)
                    VALUES (:name, :description, :product_category_id_fk, :price, :weight, :length, :height, :width, :seller_id)
                """
                execute_timed_query(db_session, query, {'name': name, 'description': description, 
                                                       'product_category_id_fk': category, 'weight': weight, 
                                                       'length': length, 'height': height, 'width': width, 
                                                       'price': price, 'seller_id': seller_id})

                product_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                # Insert the product image
                query = """
                    INSERT INTO product_image (product_id_fk, image_link)
                    VALUES (:product_id, :image_link)
                """
                execute_timed_query(db_session, query, {'product_id': product_id, 'image_link': image_data})

                db_session.commit()

                return redirect(url_for('dashboard'))
            
            except Exception as e:
                return f"An error occurred: {str(e)}"

    return render_template('add_product.html')



@app.route('/view_sales')
@login_required
def view_sales():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    seller_id = session['seller_id']

    try:
        # Query to get the number of sales per product along with product details for the logged-in seller
        query = """
            SELECT 
                p.id as product_id, 
                p.name as product_name, 
                pi.image_link, 
                COALESCE(sales.sales_count, 0) as sales_count
            FROM product p
            LEFT JOIN product_image pi ON p.id = pi.product_id_fk
            LEFT JOIN (
                SELECT oi.product_id_fk, COUNT(oi.product_id_fk) as sales_count
                FROM order_item oi
                GROUP BY oi.product_id_fk
            ) as sales ON p.id = sales.product_id_fk
            WHERE p.seller_id_fk = :seller_id
        """
        sales_data = execute_timed_query(db_session, query, {'seller_id': seller_id}).fetchall()

        return render_template('view_sales.html', sales_data=sales_data)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route('/view_product_sales/<int:product_id>')
@login_required
def view_product_sales(product_id):
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    seller_id = session['seller_id']

    try:
        # Query to get order details for a specific product sold by the seller
        query = """
            SELECT o.id as order_id, p.id as product_id, o.purchased_at, u.username as customer_username,
                   CASE WHEN orv.id IS NOT NULL THEN 1 ELSE 0 END AS has_review
            FROM order_item oi
            JOIN `order` o ON oi.order_id_fk = o.id
            JOIN user u ON o.customer_id_fk = u.customer_id_fk
            JOIN product p ON oi.product_id_fk = p.id
            LEFT JOIN order_review orv ON o.id = orv.order_id_fk
            WHERE p.seller_id_fk = :seller_id AND p.id = :product_id
        """
        product_sales = execute_timed_query(db_session, query, {'seller_id': seller_id, 'product_id': product_id}).fetchall()
        has_sales = len(product_sales) > 0

        return render_template('product_sales.html', product_sales=product_sales, has_sales=has_sales)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/view_order_review_seller/<int:order_id>')
@login_required
def view_order_review_seller(order_id):
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    try:
        # Fetch the review for the given order_id
        query_review = """
            SELECT * FROM order_review WHERE order_id_fk = :order_id
        """
        order_review = execute_timed_query(db_session, query_review, {'order_id': order_id}).fetchone()

        # Fetch the order item associated with the order
        query_order_item = """
            SELECT * FROM order_item WHERE order_id_fk = :order_id
        """
        order_item = execute_timed_query(db_session, query_order_item, {'order_id': order_id}).fetchone()

        return render_template('view_order_review_seller.html', order_review=order_review, order_item=order_item)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route('/shop', methods=['GET', 'POST'])
@login_required
def shop():
    if 'role' not in session:
        return redirect(url_for('login'))

    user_role = session.get('role')

    # If the user is a customer, handle the creation of shopping sessions
    if user_role == 'customer':
        customer_id = session.get('customer_id')
        if not customer_id:
            return redirect(url_for('login'))

        active_session = db_session.execute(
            text("SELECT * FROM shopping_session WHERE customer_id_fk = :customer_id"),
            {'customer_id': customer_id}
        ).fetchone()

        if not active_session:
            db_session.execute(
                text("""
                    INSERT INTO shopping_session (customer_id_fk, created_at, total_amount) 
                    VALUES (:customer_id, :created_at, 0)
                """),
                {'customer_id': customer_id, 'created_at': datetime.now()}
            )
            db_session.commit()
            active_session = db_session.execute(
                text("SELECT * FROM shopping_session WHERE customer_id_fk = :customer_id ORDER BY created_at DESC LIMIT 1"),
                {'customer_id': customer_id}
            ).fetchone()

        session['shopping_session_id'] = active_session.id

    elif user_role == 'seller':
        seller_id = session.get('seller_id')
        if not seller_id:
            return redirect(url_for('login'))

    search = request.form.get('search', '')
    category = request.form.get('category', '')
    price_min = request.form.get('price_min', '')
    price_max = request.form.get('price_max', '')
    sort_by = request.form.get('sort_by', '')

    # Define the base query for products
    query = """
        SELECT p.id, p.name, p.description, p.price, pi.image_link, u.username
        FROM product p
        JOIN product_image pi ON p.id = pi.product_id_fk
        JOIN user u ON p.seller_id_fk = u.seller_id_fk
        WHERE p.name LIKE :search
    """
    params = {'search': '%' + search + '%'}

    if category:
        query += " AND p.product_category_id_fk = :category"
        params['category'] = category

    if price_min:
        query += " AND p.price >= :price_min"
        params['price_min'] = float(price_min)

    if price_max:
        query += " AND p.price <= :price_max"
        params['price_max'] = float(price_max)

    if sort_by:
        if sort_by == 'price_asc':
            query += " ORDER BY p.price ASC"
        elif sort_by == 'price_desc':
            query += " ORDER BY p.price DESC"
        elif sort_by == 'name_asc':
            query += " ORDER BY p.name ASC"
        elif sort_by == 'name_desc':
            query += " ORDER BY p.name DESC"

    products = execute_timed_query(db_session, query, params).fetchall()

    categories = db_session.execute(text("SELECT id, name FROM product_category")).fetchall()

    return render_template('shop.html', products=products, categories=categories, user_role=user_role)

@app.route('/product/<int:product_id>')
def product(product_id):
    query = """
        SELECT p.id, p.name, p.description, p.weight, p.length, p.width, p.price, pi.image_link  
        FROM product p
        JOIN product_image pi ON p.id = pi.product_id_fk
        WHERE p.id = :product_id
    """
    product = execute_timed_query(db_session, query, {'product_id': product_id}).fetchone()
    
    return render_template('product.html', product=product)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if 'seller_id' not in session:
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        weight = request.form['weight']
        length = request.form['length']
        height = request.form['height']
        width = request.form['width']
        
        query_update = """
            UPDATE product 
            SET name = :name, description = :description, weight = :weight, 
                length = :length, height = :height, width = :width 
            WHERE id = :product_id
        """
        db_session.execute(text(query_update), {'name': name, 'description': description, 
                                                'weight': weight, 'length': length, 
                                                'height': height, 'width': width, 
                                                'product_id': product_id})
        db_session.commit()
        
        return redirect(url_for('dashboard'))
    
    query_product = """
        SELECT p.* 
        FROM product p
        JOIN order_item oi ON p.id = oi.product_id_fk
        WHERE p.id = :product_id AND p.seller_id_fk = :seller_id
    """
    product = execute_timed_query(db_session, query_product, {'product_id': product_id, 'seller_id': seller_id}).fetchone()
    
    return render_template('edit_product.html', product=product)



@app.route('/order/<int:order_id>/payment')
@login_required
def order_payment(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    order_payment = db_session.execute(text("SELECT * FROM order_payment WHERE order_id_fk = :order_id"), {'order_id': order_id}).fetchall()
    
    return render_template('order_payment.html', order_payment=order_payment)

@app.route('/order/<int:order_id>/review')
@login_required
def order_review(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    order_review = db_session.execute(text("SELECT * FROM order_review WHERE order_id_fk = :order_id"), {'order_id': order_id}).fetchall()
    
    return render_template('order_review.html', order_review=order_review)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    quantity = int(request.form.get('quantity', 1))

    # Check if the item is already in the cart
    query_check_cart = """
        SELECT * FROM cart_item WHERE session_id_fk = :session_id AND product_id_fk = :product_id
    """
    result = execute_timed_query(db_session, query_check_cart, {'session_id': shopping_session_id, 'product_id': product_id})
    cart_item = result.fetchone()

    if cart_item:
        # Update quantity if item is already in the cart
        new_quantity = cart_item.quantity + quantity
        query_update_cart = """
            UPDATE cart_item SET quantity = :quantity WHERE session_id_fk = :session_id AND product_id_fk = :product_id
        """
        db_session.execute(text(query_update_cart), {'quantity': new_quantity, 'session_id': shopping_session_id, 'product_id': product_id})
    else:
        # Add new item to the cart
        query_insert_cart = """
            INSERT INTO cart_item (session_id_fk, product_id_fk, quantity) VALUES (:session_id, :product_id, :quantity)
        """
        db_session.execute(text(query_insert_cart), {'session_id': shopping_session_id, 'product_id': product_id, 'quantity': quantity})

    # Update total amount in the shopping session
    query_update_total_amount = """
        UPDATE shopping_session 
        SET total_amount = (
            SELECT SUM(p.price * ci.quantity) 
            FROM cart_item ci 
            JOIN product p ON ci.product_id_fk = p.id 
            WHERE ci.session_id_fk = :session_id
        ) 
        WHERE id = :session_id
    """
    db_session.execute(text(query_update_total_amount), {'session_id': shopping_session_id})

    db_session.commit()

    return redirect(url_for('view_cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    quantity = int(request.form.get('quantity', 1))

    if quantity < 1:
        quantity = 1

    try:
        # Update the quantity of the item in the cart
        db_session.execute(text("""
            UPDATE cart_item SET quantity = :quantity WHERE session_id_fk = :session_id AND product_id_fk = :product_id
        """), {'quantity': quantity, 'session_id': shopping_session_id, 'product_id': product_id})

        # Update total amount in the shopping session
        db_session.execute(text("""
            UPDATE shopping_session 
            SET total_amount = (
                SELECT SUM(p.price * ci.quantity) 
                FROM cart_item ci
                JOIN product p ON ci.product_id_fk = p.id
                WHERE ci.session_id_fk = :session_id
            )
            WHERE id = :session_id
        """), {'session_id': shopping_session_id})

        db_session.commit()
        flash('Cart updated successfully', 'success')
    except Exception as e:
        db_session.rollback()
        flash('An error occurred while updating the cart', 'danger')
        print(f"Error: {e}")

    return redirect(url_for('view_cart'))


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    # Delete the item from the cart
    query_delete_cart_item = """
        DELETE FROM cart_item 
        WHERE session_id_fk = :session_id AND product_id_fk = :product_id
    """
    execute_timed_query(db_session, query_delete_cart_item, {'session_id': shopping_session_id, 'product_id': product_id})
    
    # Update the total amount
    query_update_total_amount = """
        UPDATE shopping_session 
        SET total_amount = (
            SELECT SUM(p.price * ci.quantity) 
            FROM cart_item ci
            JOIN product p ON ci.product_id_fk = p.id
            WHERE ci.session_id_fk = :session_id
        ) 
        WHERE id = :session_id
    """
    db_session.execute(text(query_update_total_amount), {'session_id': shopping_session_id})

    db_session.commit()

    return redirect(url_for('view_cart'))


@app.route('/cart')
@login_required
def view_cart():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    # Retrieve cart items
    query_cart_items = """
        SELECT p.id, p.name, p.price, ci.quantity, (p.price * ci.quantity) as total_price
        FROM cart_item ci
        JOIN product p ON ci.product_id_fk = p.id
        WHERE ci.session_id_fk = :session_id
    """
    cart_items = execute_timed_query(db_session, query_cart_items, {'session_id': shopping_session_id}).fetchall()

    # Retrieve total amount
    query_total_amount = """
        SELECT total_amount FROM shopping_session WHERE id = :session_id
    """
    total_amount = db_session.execute(text(query_total_amount), {'session_id': shopping_session_id}).scalar()

    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)


def ensure_payment_types():
    payment_types = ['Visa', 'Credit Card', 'Paynow']
    existing_payment_types = db_session.execute(text("""
        SELECT payment_name FROM payment_type
    """)).fetchall()
    
    existing_payment_names = [ptype[0] for ptype in existing_payment_types]
    
    for payment_type in payment_types:
        if payment_type not in existing_payment_names:
            query_insert_payment_type = """
                INSERT INTO payment_type (payment_name) VALUES (:payment_name)
            """
            execute_timed_query(db_session, query_insert_payment_type, {'payment_name': payment_type})
            
    db_session.commit()

ensure_payment_types()

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    shopping_session_id = session.get('shopping_session_id')
    if not shopping_session_id:
        return redirect(url_for('shop'))

    if request.method == 'POST':
        # Handle the POST request for checkout
        order_id = request.form['order_id']
        payment_type_id = request.form['payment_type_id']

        # Insert into order_payment
        query_insert_order_payment = """
            INSERT INTO order_payment (order_id_fk, payment_type_id_fk)
            VALUES (:order_id, :payment_type_id)
        """
        execute_timed_query(db_session, query_insert_order_payment, {'order_id': order_id, 'payment_type_id': payment_type_id})
        
        # Update order status and purchase date
        query_update_order_status = """
            UPDATE `order`
            SET order_status = 'paid', purchased_at = :purchased_at
            WHERE id = :order_id
        """
        db_session.execute(text(query_update_order_status), {'order_id': order_id, 'purchased_at': datetime.now()})
        
        # Commit the transaction
        db_session.commit()

        return redirect(url_for('shop'))
    else:
        # Handle the GET request for showing the checkout page
        # Create an order
        customer_id = session['customer_id']
        query_insert_order = """
            INSERT INTO `order` (customer_id_fk, order_status)
            VALUES (:customer_id, 'unpaid')
        """
        db_session.execute(text(query_insert_order), {'customer_id': customer_id})
        db_session.commit()
        
        order_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # Fetch cart items for summary
        query_cart_items = """
            SELECT p.name, p.price, ci.quantity, (p.price * ci.quantity) as total_price
            FROM cart_item ci
            JOIN product p ON ci.product_id_fk = p.id
            WHERE ci.session_id_fk = :session_id
        """
        cart_items = execute_timed_query(db_session, query_cart_items, {'session_id': shopping_session_id}).fetchall()

        # Calculate total amount from the cart items
        total_amount = sum(item.total_price for item in cart_items)

        return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, order_id=order_id)



@app.route('/process_checkout', methods=['POST'])
@login_required
def process_checkout():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    order_id = request.form['order_id']
    total_amount = request.form['total_amount']
    return redirect(url_for('payment', order_id=order_id, total_amount=total_amount))


@app.route('/payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def payment(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    total_amount = request.args.get('total_amount')
    payment_types = db_session.execute(text("SELECT * FROM payment_type")).fetchall()
    
    return render_template('payment.html', order_id=order_id, total_amount=total_amount, payment_types=payment_types)


@app.route('/process_payment/<int:order_id>', methods=['POST'])
@login_required
def process_payment(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    payment_type_id = request.form['payment_type_id']

    # Get total_amount from shopping session using customer_id_fk from the order table
    query_total_amount = """
        SELECT total_amount
        FROM shopping_session
        WHERE customer_id_fk = (SELECT customer_id_fk FROM `order` WHERE id = :order_id)
    """
    total_amount = db_session.execute(text(query_total_amount), {'order_id': order_id}).scalar()

    # Insert into order_payment with total_amount as payment_value
    query_insert_order_payment = """
        INSERT INTO order_payment (order_id_fk, payment_type_id_fk, payment_value)
        VALUES (:order_id, :payment_type_id, :total_amount)
    """
    execute_timed_query(db_session, query_insert_order_payment, {'order_id': order_id, 'payment_type_id': payment_type_id, 'total_amount': total_amount})
    
    # Update order status and purchase date
    query_update_order_status = """
        UPDATE `order`
        SET order_status = 'paid', purchased_at = :purchased_at
        WHERE id = :order_id
    """
    db_session.execute(text(query_update_order_status), {'order_id': order_id, 'purchased_at': datetime.now()})
    
    # Insert rows into order_item for each product in the cart
    shopping_session_id = session.get('shopping_session_id')
    query_cart_items = """
        SELECT product_id_fk, quantity FROM cart_item WHERE session_id_fk = :session_id
    """
    cart_items = db_session.execute(text(query_cart_items), {'session_id': shopping_session_id}).fetchall()

    for item in cart_items:
        query_insert_order_item = """
            INSERT INTO order_item (order_id_fk, product_id_fk, quantity)
            VALUES (:order_id, :product_id, :quantity)
        """
        db_session.execute(text(query_insert_order_item), {'order_id': order_id, 'product_id': item.product_id_fk, 'quantity': item.quantity})
    
    # Remove items from cart
    query_delete_cart_items = """
        DELETE FROM cart_item 
        WHERE session_id_fk = :session_id
    """
    db_session.execute(text(query_delete_cart_items), {'session_id': shopping_session_id})
    
    # Update the total amount in the shopping session
    query_update_shopping_session = """
        UPDATE shopping_session 
        SET total_amount = 0 
        WHERE id = :session_id
    """
    db_session.execute(text(query_update_shopping_session), {'session_id': shopping_session_id})

    # Commit the transaction
    db_session.commit()

    return redirect(url_for('shop'))



@app.route('/view_orders')
@login_required
def view_orders():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    customer_id = session['customer_id']
    
    # Query to get all orders for the customer with their payment value and review status
    orders = db_session.execute(text("""
        SELECT o.id, o.purchased_at, o.order_status, op.payment_value,
               CASE WHEN orv.id IS NOT NULL THEN 1 ELSE 0 END AS has_review,
               orv.score, orv.title, orv.content
        FROM `order` o
        JOIN order_payment op ON o.id = op.order_id_fk
        LEFT JOIN order_review orv ON o.id = orv.order_id_fk
        WHERE o.customer_id_fk = :customer_id
    """), {'customer_id': customer_id}).fetchall()

    return render_template('orders.html', orders=orders, order_has_review=order_has_review)

@app.route('/view_order_detail/<int:order_id>')
@login_required
def view_order_detail(order_id):
    # Fetch order details from the database based on order_id
    order_query = """
        SELECT o.*, op.payment_value
        FROM `order` o
        JOIN order_payment op ON o.id = op.order_id_fk
        WHERE o.id = :order_id
    """
    order = fetch_one(db_session, order_query, {'order_id': order_id})

    # Fetch order items for the selected order
    order_items_query = """
        SELECT p.name as product_name, p.price, oi.quantity, (p.price * oi.quantity) as total_price
        FROM order_item oi
        JOIN product p ON oi.product_id_fk = p.id
        WHERE oi.order_id_fk = :order_id
    """
    order_items = fetch_all(db_session, order_items_query, {'order_id': order_id})

    # Render a template to display order details
    return render_template('order_detail.html', order=order, order_items=order_items)


@app.route('/order_reviews/<int:order_id>')
@login_required
def order_reviews(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    # Fetch reviews for the given order_id
    order_reviews_query = """
        SELECT * FROM order_review WHERE order_id_fk = :order_id
    """
    order_reviews = fetch_all(db_session, order_reviews_query, {'order_id': order_id})

    return render_template('order_reviews.html', order_reviews=order_reviews)

@app.route('/view_order_review_customer/<int:order_id>')
@login_required
def view_order_review(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    # Fetch the review for the given order_id
    order_review_query = """
        SELECT * FROM order_review WHERE order_id_fk = :order_id
    """
    order_review = fetch_one(db_session, order_review_query, {'order_id': order_id})

    return render_template('view_order_review_customer.html', order_review=order_review)

@app.route('/write_order_review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def write_order_review(order_id):
    if request.method == 'POST':
        # Handle form submission to write a review
        score = request.form['score']
        title = request.form['title']
        content = request.form['content']
        created_at = datetime.now()

        db_session.execute(text("""
            INSERT INTO order_review (order_id_fk, score, title, content, created_at)
            VALUES (:order_id, :score, :title, :content, :created_at)
        """), {'order_id': order_id, 'score': score, 'title': title, 'content': content, 'created_at': created_at})

        db_session.commit()

        return redirect(url_for('view_orders'))

    else:
        # Render the form to write a review
        return render_template('write_order_review.html', order_id=order_id)
    
@app.route('/sales_report')
@login_required
@query_timer
def sales_report():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    seller_id = session['seller_id']

    query = """
    SELECT
        p.id AS product_id,
        p.name AS product_name,
        DATE_FORMAT(o.purchased_at, '%Y-%m') AS sale_month,
        SUM(oi.quantity) AS total_quantity_sold,
        SUM(oi.quantity * p.price) AS total_revenue
    FROM
        `order` o
    JOIN
        order_item oi ON o.id = oi.order_id_fk
    JOIN
        product p ON oi.product_id_fk = p.id
    WHERE
        o.order_status = 'paid' AND p.seller_id_fk = :seller_id
    GROUP BY
        p.id, p.name, sale_month
    ORDER BY
        p.id, sale_month;
    """

    sales_report = db_session.execute(text(query), {'seller_id': seller_id}).fetchall()
    return render_template('sales_report.html', sales_report=sales_report)

@app.route('/product_reviews')
@login_required
@query_timer
def product_reviews():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    seller_id = session['seller_id']

    query = """
    SELECT 
        p.id AS product_id,
        p.name AS product_name,
        COUNT(orv.id) AS review_count,
        AVG(orv.score) AS average_score
    FROM 
        product p
    JOIN 
        order_item oi ON p.id = oi.product_id_fk
    JOIN 
        `order` o ON oi.order_id_fk = o.id
    JOIN 
        order_review orv ON o.id = orv.order_id_fk
    WHERE 
        p.seller_id_fk = :seller_id
    GROUP BY 
        p.id, p.name
    ORDER BY 
        average_score DESC, review_count DESC;
    """

    product_reviews = db_session.execute(text(query), {'seller_id': seller_id}).fetchall()
    return render_template('product_reviews.html', product_reviews=product_reviews)

if __name__ == '__main__':
    app.run(debug=True)
