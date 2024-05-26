from django.contrib import admin
from .models import User, Seller, Customer, Geolocation, Product, CartItem, Order, OrderPayment, OrderReview, OrderItem, Session

# Register your models here.
admin.site.register(User)
admin.site.register(Seller)
admin.site.register(Customer)
admin.site.register(Geolocation)
admin.site.register(Product)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderPayment)
admin.site.register(OrderReview)
admin.site.register(OrderItem)
admin.site.register(Session)