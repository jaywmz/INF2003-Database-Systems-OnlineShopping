from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash
from database import engine

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
            # Convert Row object to dictionary
            user_dict = {key: value for key, value in zip(result.keys(), user)}
            if user_dict['password'] == password:  # Plain text password comparison
                if user_dict['seller_id_fk']:
                    session['seller_id'] = user_dict['seller_id_fk']
                    return redirect(url_for('dashboard'))
                elif user_dict['customer_id_fk']:
                    session['customer_id'] = user_dict['customer_id_fk']
                    return redirect(url_for('shop'))
            else:
                return "Invalid credentials"
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']  # Plain text password (not recommended)
            user_type = request.form['user_type']
            
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
            # Log the error or handle it accordingly
            return f"Missing form field: {e}"
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'seller_id' not in session:
        return redirect(url_for('login'))
    
    seller_id = session['seller_id']
    
    products = db_session.execute(text("SELECT * FROM product WHERE seller_id = :seller_id"), {'seller_id': seller_id}).fetchall()
    
    reviews = db_session.execute(text("""
        SELECT r.*, p.name AS product_name 
        FROM order_review r 
        JOIN order_item oi ON r.order_id_fk = oi.id 
        JOIN product p ON oi.product_id_fk = p.id 
        WHERE p.seller_id = :seller_id
    """), {'seller_id': seller_id}).fetchall()
    
    return render_template('dashboard.html', products=products, reviews=reviews)

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
            WHERE id = :product_id AND seller_id = :seller_id
        """), {'name': name, 'description': description, 'weight': weight, 'length': length, 'height': height, 'width': width, 'product_id': product_id, 'seller_id': seller_id})
        db_session.commit()
        
        return redirect(url_for('dashboard'))
    
    product = db_session.execute(text("SELECT * FROM product WHERE id = :product_id AND seller_id = :seller_id"), {'product_id': product_id, 'seller_id': seller_id}).fetchone()
    
    return render_template('edit_product.html', product=product)

@app.route('/shop')
def shop():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
    
    products = db_session.execute(text("SELECT * FROM product")).fetchall()
    
    return render_template('shop.html', products=products)

if __name__ == '__main__':
    app.run(debug=True)
