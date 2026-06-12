from rest_framework import serializers
from .models import Category, Product, Order, OrderItem, CustomerProfile, OrderStatusHistory, StockMovement


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'stock',
            'category',
            'category_name',
            'image',
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    item_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'product',
            'product_name',
            'quantity',
            'item_total',
        ]

    def get_item_total(self, obj):
        return obj.product.price * obj.quantity
    
    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity')

        if quantity <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )

        if product.stock < quantity:
            raise serializers.ValidationError(
                "Not enough stock available."
            )

        return data
    
class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )

    quantity = serializers.IntegerField(min_value=1)  

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source='changed_by.username',
        read_only=True
    )

    class Meta:
        model = OrderStatusHistory
        fields = [
            'id',
            'old_status',
            'new_status',
            'changed_by',
            'changed_by_username',
            'changed_at',
            'note',
        ]          


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True
    )

    status_history = OrderStatusHistorySerializer(
    many=True,
    read_only=True
)

    order_items = OrderItemCreateSerializer(
        many=True,
        write_only=True
    )
    city = serializers.CharField(
    required=False,
    allow_blank=True
)
    
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    phone_number = serializers.CharField(
    required=False,
    allow_blank=True
)

    use_saved_phone = serializers.BooleanField(
        write_only=True,
        required=False,
        default=True
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'username',
            'customer_name',
            'city',
            'phone_number',
            'use_saved_phone',
            'notes',
            'total_price',
            'status',
            'created_at',
            'items',
            'order_items',
            'status_history',
        ]

        read_only_fields = [
            'user',
            'total_price',
        ]

    def validate(self, data):
        request = self.context.get('request')

        order_items = data.get('order_items', [])

        if not order_items:
            raise serializers.ValidationError(
                "At least one product is required to create an order."
            )

        for item in order_items:
            product = item['product']
            quantity = item['quantity']

            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"Not enough stock for product: {product.name}"
                )

        if request and request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            use_saved_phone = data.get('use_saved_phone', True)

            if use_saved_phone:
                if profile and profile.phone_number:
                    return data

                raise serializers.ValidationError(
                    "No saved phone number found. Please enter a phone number."
                )

            if not data.get('phone_number'):
                raise serializers.ValidationError(
                    "Phone number is required when not using the saved number."
                )

            return data

        if not data.get('customer_name'):
            raise serializers.ValidationError(
                "Customer name is required for guest orders."
            )

        if not data.get('city'):
            raise serializers.ValidationError(
                "City is required for guest orders."
            )

        if not data.get('phone_number'):
            raise serializers.ValidationError(
                "Phone number is required for guest orders."
            )

        return data

    def create(self, validated_data):
        order_items = validated_data.pop('order_items')
        validated_data.pop('use_saved_phone', None)

        order = Order.objects.create(**validated_data)

        for item in order_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity']
            )

        order.update_total_price()

        return order
    

class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'product',
            'product_name',
            'order',
            'quantity_change',
            'reason',
            'created_at',
            'note',
        ]