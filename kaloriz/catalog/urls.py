from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('search/', views.search, name='search'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('apply-discount/', views.apply_discount, name='apply_discount'),
]
