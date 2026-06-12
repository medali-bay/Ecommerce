from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.db.models import Sum
from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, Order, OrderItem, CustomerProfile, OrderStatusHistory, StockMovement
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
    StockMovementSerializer,
)
from .permissions import IsAdminOrReadOnly
from .filters import ProductFilter


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        'name',
        'description',
        'category__name',
    ]

    ordering_fields = [
        'price',
        'stock',
        'name',
    ]

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response(
                {"error": "Only admin can adjust stock."},
                status=status.HTTP_403_FORBIDDEN
            )

        product = self.get_object()

        quantity_change = request.data.get('quantity_change')
        note = request.data.get('note', '')

        if quantity_change is None:
            return Response(
                {"error": "quantity_change is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity_change = int(quantity_change)
        except ValueError:
            return Response(
                {"error": "quantity_change must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if product.stock + quantity_change < 0:
            return Response(
                {"error": "Stock cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.stock += quantity_change
        product.save()

        StockMovement.objects.create(
            product=product,
            quantity_change=quantity_change,
            reason='manual_adjustment',
            note=note
        )

        return Response(
            {
                "message": "Stock adjusted successfully.",
                "product": product.name,
                "new_stock": product.stock,
                "quantity_change": quantity_change,
            },
            status=status.HTTP_200_OK
        )


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        'status',
    ]

    ordering_fields = [
        'created_at',
        'total_price',
    ]

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated and user.is_staff:
            return Order.objects.all()

        if user.is_authenticated:
            return Order.objects.filter(user=user)

        return Order.objects.none()

    def is_admin(self, request):
        return request.user.is_authenticated and request.user.is_staff

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            profile, created = CustomerProfile.objects.get_or_create(
                user=self.request.user
            )

            use_saved_phone = serializer.validated_data.pop(
                'use_saved_phone',
                True
            )

            if use_saved_phone:
                phone_number = profile.phone_number
                city = profile.city
            else:
                phone_number = serializer.validated_data.get('phone_number')
                city = serializer.validated_data.get('city', profile.city)

                profile.phone_number = phone_number

                if city:
                    profile.city = city

                profile.save()

            serializer.save(
                user=self.request.user,
                customer_name=self.request.user.username,
                city=city,
                phone_number=phone_number
            )

        else:
            serializer.save(user=None)

    @action(detail=True, methods=['post'])
    def validate_order(self, request, pk=None):
        if not self.is_admin(request):
            return Response(
                {"error": "Only admin can validate orders."},
                status=status.HTTP_403_FORBIDDEN
            )

        order = self.get_object()

        if order.status != 'pending':
            return Response(
                {"error": "Only pending orders can be validated."},
                status=status.HTTP_400_BAD_REQUEST
            )
        old_status = order.status
        order.status = 'validated'
        order.save()

        OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status='validated',
        changed_by=request.user,
        note='Order validated by admin.'
    )

        return Response(
            {"message": "Order validated successfully."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
     if not self.is_admin(request):
        return Response(
            {"error": "Only admin can cancel orders."},
            status=status.HTTP_403_FORBIDDEN
        )

     order = self.get_object()

     if order.status in ['cancelled', 'delivered']:
        return Response(
            {"error": "This order can no longer be cancelled."},
            status=status.HTTP_400_BAD_REQUEST
        )

     old_status = order.status

     for item in order.items.all():
      product = item.product
      product.stock += item.quantity
      product.save()

      StockMovement.objects.create(
        product=product,
        order=order,
        quantity_change=item.quantity,
        reason='order_cancelled',
        note=f"Order #{order.id} cancelled. Stock restored."
    )

     order.status = 'cancelled'
     order.save()

     OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status='cancelled',
        changed_by=request.user,
        note='Order cancelled by admin. Stock restored.'
    )

     return Response(
        {"message": "Order cancelled successfully. Stock restored."},
        status=status.HTTP_200_OK
    )

    @action(detail=True, methods=['post'])
    def deliver_order(self, request, pk=None):
        if not self.is_admin(request):
            return Response(
                {"error": "Only admin can mark orders as delivered."},
                status=status.HTTP_403_FORBIDDEN
            )

        order = self.get_object()

        if order.status != 'validated':
            return Response(
                {"error": "Only validated orders can be delivered."},
                status=status.HTTP_400_BAD_REQUEST
            )
        old_status = order.status
        order.status = 'delivered'
        order.save()

        OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status='delivered',
        changed_by=request.user,
        note='Order marked as delivered by admin.'
    )

        return Response(
            {"message": "Order marked as delivered successfully."},
            status=status.HTTP_200_OK
        )

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer



class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_orders = Order.objects.count()

        pending_orders = Order.objects.filter(status='pending').count()
        validated_orders = Order.objects.filter(status='validated').count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        cancelled_orders = Order.objects.filter(status='cancelled').count()

        total_revenue = Order.objects.filter(
            status='delivered'
        ).aggregate(
            total=Sum('total_price')
        )['total'] or 0

        low_stock_products = Product.objects.filter(
            stock__lte=5
        ).count()

        return Response({
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "validated_orders": validated_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": total_revenue,
            "low_stock_products": low_stock_products,
        })

class LowStockProductsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        products = Product.objects.filter(stock__lte=5)
        serializer = ProductSerializer(products, many=True)

        return Response(serializer.data)

class RevenueReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        delivered_orders = Order.objects.filter(status='delivered')

        if start_date:
            delivered_orders = delivered_orders.filter(
                created_at__date__gte=start_date
            )

        if end_date:
            delivered_orders = delivered_orders.filter(
                created_at__date__lte=end_date
            )

        total_revenue = delivered_orders.aggregate(
            total=Sum('total_price')
        )['total'] or 0

        orders_data = []

        for order in delivered_orders:
            orders_data.append({
                "order_id": order.id,
                "customer_name": order.customer_name,
                "phone_number": order.phone_number,
                "city": order.city,
                "total_price": order.total_price,
                "created_at": order.created_at,
            })

        return Response({
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue,
            "delivered_orders_count": delivered_orders.count(),
            "orders": orders_data,
        })

class BestSellingProductsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        order_items = OrderItem.objects.filter(
            order__status='delivered'
        )

        if start_date:
            order_items = order_items.filter(
                order__created_at__date__gte=start_date
            )

        if end_date:
            order_items = order_items.filter(
                order__created_at__date__lte=end_date
            )

        best_sellers = (
            order_items
            .values('product__id', 'product__name')
            .annotate(total_quantity=Sum('quantity'))
            .order_by('-total_quantity')
        )

        return Response({
            "start_date": start_date,
            "end_date": end_date,
            "products": best_sellers,
        })

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAdminUser]