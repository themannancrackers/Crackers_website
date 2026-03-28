"""
URL configuration for crackers_ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from inventory.views import home, handle_404, handle_500, handle_403, handle_400, handle_connection_error, handle_maintenance, serve_media

from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from inventory.sitemaps import ProductSitemap, StaticViewSitemap

sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}

from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    logout(request)
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/logout/', custom_logout, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),  # Add this line for profile URLs
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('', home, name='home'),  # Home page
    
    # SEO
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # Error pages
    path('error/404/', handle_404, name='error_404'),
    path('error/500/', handle_500, name='error_500'),
    path('error/403/', handle_403, name='error_403'),
    path('error/400/', handle_400, name='error_400'),
    path('error/connection/', handle_connection_error, name='error_connection'),
    path('error/maintenance/', handle_maintenance, name='error_maintenance'),
    
    # Media file serving (works even when DEBUG=False)
    re_path(r'^media/(?P<path>.*)$', serve_media, name='serve_media'),
]

# Only serve static files in development
# WhiteNoise middleware and web servers handle this in production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = handle_404
handler500 = handle_500
handler403 = handle_403
handler400 = handle_400
