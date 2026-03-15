from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return ['home', 'inventory:home'] # Add other named URLs here

    def location(self, item):
        return reverse(item)
