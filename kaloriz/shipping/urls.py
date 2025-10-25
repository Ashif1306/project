from django.urls import path
from . import views

app_name = 'shipping'

urlpatterns = [
    # Legacy JSON API Endpoints (District-based)
    path('districts/', views.get_districts, name='get_districts'),
    path('quotes/', views.get_shipping_quotes, name='get_quotes'),

    # RajaOngkir API Endpoints (Sulawesi Selatan)
    path('api/sulsel/cities', views.api_sulsel_cities, name='api_sulsel_cities'),
    path('api/sulsel/subdistricts', views.api_sulsel_subdistricts, name='api_sulsel_subdistricts'),
    path('api/quote', views.quote_by_params, name='shipping_quote_params'),
    path('api/quote-by-address', views.quote_by_address, name='shipping_quote_by_address'),
]
