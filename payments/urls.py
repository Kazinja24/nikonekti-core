from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet,
    RentInvoiceViewSet,
    ListingPlanViewSet,
    ListingPaymentIntentViewSet,
)

router = DefaultRouter()
router.register('invoices', RentInvoiceViewSet, basename='invoices')
router.register('pay', PaymentViewSet, basename='payments')
router.register('listing-plans', ListingPlanViewSet, basename='listing-plans')
router.register('listing-intents', ListingPaymentIntentViewSet, basename='listing-intents')

urlpatterns = router.urls
