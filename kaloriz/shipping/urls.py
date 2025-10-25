from django.urls import path
from . import views

app_name = 'shipping'

urlpatterns = [
    # JSON API Endpoints
    path('districts/', views.get_districts, name='get_districts'),
    path('quotes/', views.get_shipping_quotes, name='get_quotes'),
]
