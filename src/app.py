from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create a configured "Session" class
Session = sessionmaker(bind=engine)
# Create a Session
db_session = Session()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        result = db_session.execute(text("SELECT * FROM user WHERE username = :username"), {'username': username})
        user = result.fetchone()
        
        if user:
            user_dict = {key: value for key, value in zip(result.keys(), user)}
            if check_password_hash(user_dict['password'], password):
                session['username'] = username
                if user_dict['seller_id_fk']:
                    session['seller_id'] = user_dict['seller_id_fk']
                    session['role'] = 'seller'
                    return redirect(url_for('dashboard'))
                elif user_dict['customer_id_fk']:
                    session['customer_id'] = user_dict['customer_id_fk']
                    session['role'] = 'customer'
                    return redirect(url_for('shop'))
            else:
                return "Invalid credentials"
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('seller_id', None)
    session.pop('customer_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = generate_password_hash(request.form['password'])  # Hash the password
            user_type = request.form['user_type']
            
            # Check if the username already exists
            result = db_session.execute(text("SELECT * FROM user WHERE username = :username"), {'username': username})
            if result.fetchone():
                return "Username already exists. Please choose another one."
            
            # Insert a default geolocation record and get the ID
            db_session.execute(text("""
                INSERT INTO geolocation (latitude, longitude, city, state) 
                VALUES (0.0, 0.0, 'Default City', 'Default State')
            """))
            db_session.commit()
            geolocation_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
            if user_type == 'seller':
                db_session.execute(text("INSERT INTO seller (geolocation_fk) VALUES (:geolocation_id)"), {'geolocation_id': geolocation_id})
                db_session.commit()
                seller_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                db_session.execute(text("INSERT INTO user (username, password, seller_id_fk) VALUES (:username, :password, :seller_id)"),
                                   {'username': username, 'password': password, 'seller_id': seller_id})
            elif user_type == 'customer':
                db_session.execute(text("INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)"), {'geolocation_id': geolocation_id})
                db_session.commit()
                customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                db_session.execute(text("INSERT INTO user (username, password, customer_id_fk) VALUES (:username, :password, :customer_id)"),
                                   {'username': username, 'password': password, 'customer_id': customer_id})
        
            db_session.commit()
            return redirect(url_for('login'))
        except KeyError as e:
            return f"Missing form field: {e}"
    
    return render_template('register.html')

# Add role-based access control to dashboard and shop routes
@app.route('/dashboard')
def dashboard():
    if 'seller_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    
    products = db_session.execute(text("""
        SELECT p.* 
        FROM product p
        JOIN order_item oi ON p.id = oi.product_id_fk
        WHERE oi.seller_id_fk = :seller_id
    """), {'seller_id': seller_id}).fetchall()
    
    return render_template('dashboard.html', products=products)

import base64

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
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

            query = """
                INSERT INTO product (name, description, product_category_id_fk, price, weight, length, height, width)
                VALUES (:name, :description, :product_category_id_fk, :price, :weight, :length, :height, :width)
            """
            db_session.execute(text(query), {'name': name, 'description': description, 
                                             'product_category_id_fk': category, 'weight': weight, 'length': length, 
                                             'height': height, 'width': width, 'price': price})

            product_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            query = """
                INSERT INTO product_image (product_id_fk, image_link)
                VALUES (:product_id, :image_link)
            """
            db_session.execute(text(query), {'product_id': product_id, 'image_link': image_data})

            db_session.commit()

            return redirect(url_for('shop'))

    return render_template('add_product.html')



@app.route('/shop', methods=['GET', 'POST'])
def shop():
   # if 'customer_id' not in session or session.get('role') != 'customer':
       # return redirect(url_for('login'))

    search = request.form.get('search')
    print(f"Search term: {search}")  # Debug print

    if search:
        query = """
            SELECT p.id, p.name, p.description, p.price, pi.image_link
            FROM product p
            JOIN product_image pi ON p.id = pi.product_id_fk
            WHERE p.name LIKE :search
        """
        products = db_session.execute(text(query), {'search': '%' + search + '%'}).fetchall()
        print(f"Products found: {products}")  # Debug print
    else:
        query = """
            SELECT p.id, p.name, p.description, p.price, pi.image_link
            FROM product p
            JOIN product_image pi ON p.id = pi.product_id_fk
        """
        products = db_session.execute(text(query)).fetchall()
        print(f"All products: {products}")  # Debug print

    return render_template('shop.html', products=products)





@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
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
        
        db_session.execute(text("""
            UPDATE product 
            SET name = :name, description = :description, weight = :weight, 
                length = :length, height = :height, width = :width 
            WHERE id = :product_id
        """), {'name': name, 'description': description, 'weight': weight, 'length': length, 'height': height, 'width': width, 'product_id': product_id})
        db_session.commit()
        
        return redirect(url_for('dashboard'))
    
    product = db_session.execute(text("""
        SELECT p.* 
        FROM product p
        JOIN order_item oi ON p.id = oi.product_id_fk
        WHERE p.id = :product_id AND oi.seller_id_fk = :seller_id
    """), {'product_id': product_id, 'seller_id': seller_id}).fetchone()
    
    return render_template('edit_product.html', product=product)

# Add routes for order, order_payment, and order_review
@app.route('/orders')
def orders():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    customer_id = session['customer_id']
    orders = db_session.execute(text("SELECT * FROM `order` WHERE customer_id_fk = :customer_id"), {'customer_id': customer_id}).fetchall()
    
    return render_template('orders.html', orders=orders)

@app.route('/order/<int:order_id>/payment')
def order_payment(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    order_payment = db_session.execute(text("SELECT * FROM order_payment WHERE order_id_fk = :order_id"), {'order_id': order_id}).fetchall()
    
    return render_template('order_payment.html', order_payment=order_payment)

@app.route('/order/<int:order_id>/review')
def order_review(order_id):
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    order_review = db_session.execute(text("SELECT * FROM order_review WHERE order_id_fk = :order_id"), {'order_id': order_id}).fetchall()
    
    return render_template('order_review.html', order_review=order_review)

if __name__ == '__main__':
    app.run(debug=True)
