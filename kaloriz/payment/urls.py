from django.urls import path

from . import views

app_name = "payment"

urlpatterns = [
    path("create-snap-token/", views.payment_create_snap_token, name="create_snap_token"),
    path("doku/create-payment/", views.payment_create_doku_payment, name="create_doku_payment"),
    path("finish/", views.payment_finish, name="finish"),
]
