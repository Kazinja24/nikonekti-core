from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PaymentViewSet

router = DefaultRouter()
router.register('invoices', InvoiceViewSet, basename='invoices')
router.register('pay', PaymentViewSet, basename='payments')

urlpatterns = router.urls
