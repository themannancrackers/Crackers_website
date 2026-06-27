from .models import SiteConfiguration

def site_settings(request):
    try:
        min_order = SiteConfiguration.get_min_order_amount()
    except Exception:
        min_order = 1999
    return {
        'min_order_amount': min_order
    }
