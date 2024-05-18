from django.db import models

class User(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    seller_id = models.IntegerField(null=True, blank=True)
    customer_id = models.IntegerField(null=True, blank=True)

class Seller(models.Model):
    seller_id = models.AutoField(primary_key=True)
    seller_zip_code_prefix = models.CharField(max_length=20)
    seller_city = models.CharField(max_length=255)
    seller_state = models.CharField(max_length=255)

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_zip_code_prefix = models.CharField(max_length=20)
    customer_city = models.CharField(max_length=255)
    customer_state = models.CharField(max_length=255)

class Geolocation(models.Model):
    geolocation_zip_code_prefix = models.CharField(max_length=20)
    geolocation_lat = models.FloatField()
    geolocation_lng = models.FloatField()
    geolocation_city = models.CharField(max_length=255)
    geolocation_state = models.CharField(max_length=255)

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_category_name = models.CharField(max_length=255)
    product_name_length = models.IntegerField()
    product_description_length = models.IntegerField()
    product_photos_qty = models.IntegerField()
    product_weight_g = models.FloatField()
    product_length_cm = models.FloatField()
    product_height_cm = models.FloatField()
    product_width_cm = models.FloatField()

class CartItem(models.Model):
    cart_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255)
    quantity = models.IntegerField()

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_status = models.CharField(max_length=255)
    order_purchase_timestamp = models.DateTimeField()
    order_approved_at = models.DateTimeField()
    order_delivered_carrier_date = models.DateTimeField()
    order_delivered_customer_date = models.DateTimeField()
    order_estimated_delivery_date = models.DateTimeField()

class OrderPayment(models.Model):
    order_payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_sequential = models.IntegerField()
    payment_type = models.CharField(max_length=255)
    payment_installments = models.IntegerField()
    payment_value = models.FloatField()

class OrderReview(models.Model):
    review_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    review_score = models.IntegerField()
    review_comment_title = models.CharField(max_length=255)
    review_comment_message = models.TextField()
    review_creation_date = models.DateTimeField()
    review_answer_timestamp = models.DateTimeField()

class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    shipping_limit_date = models.DateTimeField()
    price = models.FloatField()
    freight_value = models.FloatField()

class Session(models.Model):
    session_id = models.CharField(max_length=255, primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total_amt = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
