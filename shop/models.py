

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)


class Product(models.Model):
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
    upload_to='products/',
    blank=True,
    null=True
)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True
    )

    customer_name = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        
    )

    notes = models.TextField(
        blank=True
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def update_total_price(self):
        total = 0

        for item in self.items.all():
            total += item.product.price * item.quantity

        self.total_price = total
        self.save()

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name or self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if self.pk:
            old_item = OrderItem.objects.get(pk=self.pk)

            if old_item.product == self.product:
                quantity_difference = self.quantity - old_item.quantity

                if quantity_difference > 0:
                    if self.product.stock >= quantity_difference:
                        self.product.stock -= quantity_difference
                        self.product.save()

                        StockMovement.objects.create(
                            product=self.product,
                            order=self.order,
                            quantity_change=-quantity_difference,
                            reason='order_created',
                            note=f"Order #{self.order.id} quantity increased."
                        )
                    else:
                        raise ValueError("Not enough stock available")

                elif quantity_difference < 0:
                    restored_quantity = abs(quantity_difference)

                    self.product.stock += restored_quantity
                    self.product.save()

                    StockMovement.objects.create(
                        product=self.product,
                        order=self.order,
                        quantity_change=restored_quantity,
                        reason='manual_adjustment',
                        note=f"Order #{self.order.id} quantity decreased."
                    )

            else:
                old_item.product.stock += old_item.quantity
                old_item.product.save()

                StockMovement.objects.create(
                    product=old_item.product,
                    order=self.order,
                    quantity_change=old_item.quantity,
                    reason='manual_adjustment',
                    note=f"Order #{self.order.id} product changed. Old product stock restored."
                )

                if self.product.stock >= self.quantity:
                    self.product.stock -= self.quantity
                    self.product.save()

                    StockMovement.objects.create(
                        product=self.product,
                        order=self.order,
                        quantity_change=-self.quantity,
                        reason='order_created',
                        note=f"Order #{self.order.id} product changed. New product stock decreased."
                    )
                else:
                    raise ValueError("Not enough stock available")

        else:
            if self.product.stock >= self.quantity:
                self.product.stock -= self.quantity
                self.product.save()

                super().save(*args, **kwargs)

                StockMovement.objects.create(
                    product=self.product,
                    order=self.order,
                    quantity_change=-self.quantity,
                    reason='order_created',
                    note=f"Order #{self.order.id} created."
                )

                self.order.update_total_price()
                return
            else:
                raise ValueError("Not enough stock available")

        super().save(*args, **kwargs)
        self.order.update_total_price()

class StockMovement(models.Model):
    REASON_CHOICES = [
        ('order_created', 'Order Created'),
        ('order_cancelled', 'Order Cancelled'),
        ('manual_adjustment', 'Manual Adjustment'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )

    quantity_change = models.IntegerField()

    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product.name}: {self.quantity_change}"

class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    phone_number = models.CharField(max_length=20)
    blank= True

    city = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return self.user.username
    
class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )

    old_status = models.CharField(
        max_length=20,
        blank=True
    )

    new_status = models.CharField(
        max_length=20
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    note = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"Order #{self.order.id}: {self.old_status} → {self.new_status}"