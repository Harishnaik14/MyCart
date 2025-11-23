from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'price', 'old_price')
	search_fields = ('name',)
	list_filter = ('price',)

admin.site.register(User, UserAdmin)
