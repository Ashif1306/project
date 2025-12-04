import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Product
from core.models import Order


class ChatbotReplyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Camilan Sehat")
        self.product = Product.objects.create(
            category=self.category,
            name="Granola Bar",
            description="Camilan rendah kalori dengan serat tinggi.",
            price=Decimal("25000"),
            stock=10,
            available=True,
        )

    def _post_message(self, message: str):
        return self.client.post(
            reverse("chatbot:chatbot_reply"),
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    def test_greeting_message_includes_closing(self):
        response = self.client.get(reverse("chatbot:chatbot_reply"))
        payload = response.json()
        self.assertIn("Halo! Saya Kaloriz", payload["reply"])
        self.assertIn("Ada yang bisa saya bantu lagi?", payload["reply"])

    def test_product_reply_lists_available_products(self):
        out_of_stock = Product.objects.create(
            category=self.category,
            name="Protein Chips",
            description="Camilan gurih tinggi protein.",
            price=Decimal("30000"),
            stock=0,
            available=True,
        )

        response = self._post_message("produk apa saja")
        reply = response.json()["reply"]

        self.assertIn("Granola Bar", reply)
        self.assertIn("Protein Chips", reply)
        self.assertIn("Produk ini sedang out of stock.", reply)
        self.assertIn("Ada yang bisa saya bantu lagi?", reply)

    def test_promo_reply_without_active_promo(self):
        response = self._post_message("ada promo nggak")
        reply = response.json()["reply"]
        self.assertIn(
            "Saat ini belum ada promo aktif, tapi pantau terus halaman promo ya!", reply
        )

    def test_promo_reply_with_discounted_product(self):
        self.product.discount_price = Decimal("20000")
        self.product.save()

        response = self._post_message("info diskon")
        reply = response.json()["reply"]
        self.assertIn("Granola Bar", reply)
        self.assertIn("diskon", reply)
        self.assertNotIn("belum ada promo", reply.lower())

    def test_tracking_requires_login(self):
        response = self._post_message("lacak pesanan")
        reply = response.json()["reply"]
        self.assertIn("silakan login dulu", reply.lower())

    def test_order_detail_detection(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="customer", email="customer@example.com", password="pass1234"
        )
        order = Order.objects.create(
            user=user,
            order_number="ORD-TEST123",
            status="shipped",
            full_name="Customer",
            email=user.email,
            phone="08123456789",
            address="Jl. Contoh 123",
            city="Jakarta",
            postal_code="12345",
            subtotal=Decimal("50000"),
            shipping_cost=Decimal("10000"),
            total=Decimal("60000"),
            shipping_provider="JNE",
            tracking_number="TRK123456789",
        )

        self.client.force_login(user)
        response = self._post_message("tolong cek ORD-TEST123 ya")
        reply = response.json()["reply"]

        self.assertIn(order.order_number, reply)
        self.assertIn("TRK123456789", reply)
        self.assertIn("Ada yang bisa saya bantu lagi?", reply)
