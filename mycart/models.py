from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager
from django.conf import settings

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    otp = models.IntegerField(null=True, blank=True)


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    old_price = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to="products/")
    description = models.TextField()

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Simple per-user cart (one cart per user)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.product} x{self.quantity}"


class Order(models.Model):
    """A simple Order record for purchases made via Buy Now or Checkout."""
    order_id = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    name = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    total = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id} ({self.user})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.IntegerField(help_text='Price per item at time of purchase')

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product} x{self.quantity} (@{self.price})"
