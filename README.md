# Online Shopping Website

This is an online shopping website built using Flask and MySQL (hosted on Heroku). It allows users to log in, view products, and leave reviews. The website also provides a dashboard for sellers to manage their products and reviews.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)

## Features

- User registration and login
- Seller dashboard for managing products and reviews
- Product listing and review functionality
- Responsive design

## Requirements

- Python 3.6+
- Flask
- MySQL Connector
- MySQL Database (Hosted on Heroku)

## Installation

Install requirements:

```bash
cd src
pip install -r requirements.txt
```

## Usage

Run the app:

```bash
python app.py
```

Open your web browser and go to [http://localhost:5000](http://localhost:5000).
Register a new user or log in with an existing account.
As a seller, you can access the dashboard to manage your products and reviews.
As a customer, you can view products and leave reviews.

## Database Schema

The database schema includes the following tables:

users: Stores user information including username, password, and roles (seller/customer).
sellers: Stores seller-specific information.
customers: Stores customer-specific information.
products: Stores product information including category, description, and dimensions.
reviews: Stores product reviews left by customers.
shopping_session: Stores shopping session information.
cart_items: Stores items added to the shopping cart.
orders: Stores order information.
order_items: Stores items included in an order.
order_payments: Stores payment information for orders.
order_reviews: Stores reviews for orders.
product_category: Stores product category information.
geolocations: Stores geolocation information for sellers and customers.

## Project Structure

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
