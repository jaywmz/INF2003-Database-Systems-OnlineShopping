# Online Shopping Website

This is an online shopping website built using Flask, MongoDB, and MySQL. It allows users to log in, view products, and leave reviews. The website also provides a dashboard for sellers to manage their products and reviews.

## Table of Contents

- [Online Shopping Website](#online-shopping-website)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Database Schema](#database-schema)
  - [Project Structure](#project-structure)
  - [Performance Analysis](#performance-analysis)
  - [Troubleshooting](#troubleshooting)

## Features

- User registration and login
- Seller dashboard for managing products and reviews
- Product listing and review functionality
- Responsive design

## Requirements

- Python 3.8+
- Flask
- MongoDB
- MySQL Database

## Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB
- MySQL
- Git

### Installation Steps

1. **Clone the Repository**:
- git clone <repository-url>
- cd <repository-directory>

2. **Create a Virtual Environment**:
- python -m venv venv
- source venv/bin/activate  
# On Windows, use `venv\Scripts\activate`

3. **Install Dependencies**:
- pip install -r requirements.txt

4. **Install MongoDB**:
- Follow the installation instructions from the official MongoDB documentation.

5. **Install MySQL**:
- Follow the installation instructions from the official MySQL documentation.

**Environment Setup**
1. **Start MongoDB**:
- mongod --dbpath /path/to/your/db

2. **Create Database and Collections**:
- Use MongoDB Compass or MongoDB shell to create the necessary database and collections.

3. Start MySQL:
- sudo service mysql start

4. Create Database and Tables:
- Use MySQL Workbench or MySQL shell to create the necessary database and tables.

**Application Configuration**
1. Set Environment Variables:
- Create a .env file in the root directory with the following content:
- FLASK_APP=app.py
- FLASK_ENV=development
- MONGO_URI=mongodb://localhost:27017/your_db
- MYSQL_URI=mysql+pymysql://username:password@localhost/your_db
SECRET_KEY=your_secret_key

**Usage**
**Running the Application**
1. **Initialize the Database**:
- flask db init
- flask db migrate
- flask db upgrade

2. **Start the Flask Application**:
- python app.py
- The application will be accessible at http://127.0.0.1:5000.

# Using the Application
# User Registration and Login
1. **Register**:
- Navigate to the registration page.
- Fill in the required details and submit the form.

2. **Login**:
- Navigate to the login page.
- Enter your credentials and log in.

# Adding Products (Seller)
1. **Add a Product**:
- Navigate to the "Add Product" page.
- Fill in the product details, upload an image, and submit the form.

# Buying Products (Customer)
1. **View Products**:
- Navigate to the "Shop" page to view available products.

2. **Add to Cart**:
- Select a product and click "Add to Cart".

3. **Checkout**:
- Go to the "Cart" page, review your items, and proceed to checkout.

4. **Process Payment**:
- Fill in payment details and complete the purchase.

# Writing Reviews (Customer)
1. **Write a Review**:
- Navigate to your orders page.
- Select an order and click "Write Review".
- Fill in the review form and submit it.

**Viewing Sales and Reviews (Seller)**
1. **View Sales**:
- Navigate to the "View Sales" page to see sales data.
2. **View Product Reviews**:
- Navigate to the "Product Reviews" page to see reviews for your products.

# Database Schema
# The database schema includes the following tables:
- users: Stores user information including username,password, and roles (seller/customer).
- sellers: Stores seller-specific information.
- customers: Stores customer-specific information.
- products: Stores product information including category, - description, and dimensions.
- reviews: Stores product reviews left by customers.
- shopping_session: Stores shopping session information.
- cart_items: Stores items added to the shopping cart.
- orders: Stores order information.
- order_items: Stores items included in an order.
- order_payments: Stores payment information for orders.
- order_reviews: Stores reviews for orders.
- product_category: Stores product category information.
- geolocations: Stores geolocation information for sellers and customers.

Project Structure
The project is structured as follows:
- src/: Contains the source code for the application.
- templates/: Contains HTML templates for the web interface.
- static/: Contains static files like CSS and JavaScript.
- config.py: Configuration file for the application.
- app.py: The main Flask application file.
plaintext

online-shopping-website/
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   └── ...
│
├── static/
│   ├── style.css
│   └── ...
│
├── app.py
├── requirements.txt
└── README.md

Image-based screenshots are available in the Microsoft Word Document NotableFeatures_D8.docx in the root directory.

# Performance Analysis
# Speed
- The application is designed to handle multiple requests concurrently using Flask's built-in server.

# Throughput
- The database operations are optimized to handle a high volume of transactions efficiently.

# Resource Utilization
- The application uses MongoDB for flexible data storage and MySQL for transactional data, balancing the load between the two databases.

# Improvements
- Future improvements could include implementing caching mechanisms and optimizing database queries to further enhance performance.

# Troubleshooting
# Common Issues
1. **Database Connection Errors**:
- Ensure MongoDB and MySQL services are running.
- Verify the database URIs in the .env file.
2. **Application Crashes**:
- Check the terminal for error messages.
- Ensure all dependencies are installed correctly.