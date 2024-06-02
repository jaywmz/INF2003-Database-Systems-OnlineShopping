from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash
from database import engine
from werkzeug.security import generate_password_hash, check_password_hash

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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            hashed_password = generate_password_hash(password)
            user_type = request.form['user_type']
            
            # Check for existing user
            result = db_session.execute(text("SELECT * FROM user WHERE username = :username"), {'username': username})
            existing_user = result.fetchone()
            if existing_user:
                return "Username already exists"

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
                db_session.execute(text("INSERT INTO user (username, password, seller_id_fk) VALUES (:username, :hashed_password, :seller_id)"),
                                   {'username': username, 'hashed_password': hashed_password, 'seller_id': seller_id})
            elif user_type == 'customer':
                db_session.execute(text("INSERT INTO customer (geolocation_id_fk) VALUES (:geolocation_id)"), {'geolocation_id': geolocation_id})
                db_session.commit()
                customer_id = db_session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                db_session.execute(text("INSERT INTO user (username, password, customer_id_fk) VALUES (:username, :hashed_password, :customer_id)"),
                                   {'username': username, 'hashed_password': hashed_password, 'customer_id': customer_id})
        
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

@app.route('/shop')
def shop():
    if 'customer_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    products = db_session.execute(text("SELECT * FROM product")).fetchall()
    
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

if __name__ == '__main__':
    app.run(debug=True)
