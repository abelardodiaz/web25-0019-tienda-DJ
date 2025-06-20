# products/admin.py
from django.contrib import admin
from .models import Brand, Category, Product, Branch, BranchStock, ExchangeRate, SyscomCredential

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('model', 'title', 'visible', 'last_sync', 'total_stock')
    search_fields = ('model', 'title')
    list_filter = ('visible', 'brand')

admin.site.register([Brand, Category, Branch, BranchStock, ExchangeRate, SyscomCredential])
