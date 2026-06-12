from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    OrderViewSet, 
    OrderItemViewSet,  
    DashboardStatsView, 
    LowStockProductsView,
    RevenueReportView,
    BestSellingProductsView,
    StockMovementViewSet, )

router = DefaultRouter()

router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('orders', OrderViewSet, basename='orders')
router.register('order-items', OrderItemViewSet)
router.register('stock-movements', StockMovementViewSet)
urlpatterns = [
    path('dashboard/stats/', DashboardStatsView.as_view()),
    path('dashboard/low-stock/', LowStockProductsView.as_view()),
    path('dashboard/revenue/', RevenueReportView.as_view()),
    path('dashboard/best-sellers/', BestSellingProductsView.as_view()),
    path('', include(router.urls)),
]