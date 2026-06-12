from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Category, Product, Order, OrderItem, StockMovement


class OrderStockTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.category = Category.objects.create(
            name="Electronics"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Mouse",
            description="Wireless mouse",
            price="25.00",
            stock=10
        )

    def test_create_order_decreases_product_stock(self):
        response = self.client.post(
            "/api/orders/",
            {
                "customer_name": "Test Customer",
                "city": "Berlin",
                "phone_number": "0123456789",
                "notes": "Testing stock decrease.",
                "order_items": [
                    {
                        "product": self.product.id,
                        "quantity": 2
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 8)

        order = Order.objects.first()
        self.assertEqual(order.total_price, self.product.price * 2)

        stock_movement = StockMovement.objects.first()
        self.assertEqual(stock_movement.quantity_change, -2)
        self.assertEqual(stock_movement.reason, "order_created")