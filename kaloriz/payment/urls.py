from django.urls import path

from . import views

app_name = "payment"

urlpatterns = [
    path("create-snap-token/", views.payment_create_snap_token, name="create_snap_token"),
    path("finish/", views.payment_finish, name="finish"),
]
