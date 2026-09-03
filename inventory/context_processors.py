from .models import SiteConfiguration

def site_settings(request):
    try:
        min_order = SiteConfiguration.get_min_order_amount()
        handling_fee_pct = SiteConfiguration.get_handling_fee_percentage()
    except Exception:
        min_order = 1999
        handling_fee_pct = 3.00
    return {
        'min_order_amount': min_order,
        'handling_fee_percentage': handling_fee_pct,
    }
