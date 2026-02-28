from rest_framework.routers import DefaultRouter
from .views import LandlordVerificationViewSet

router = DefaultRouter()
router.register(r'landlords', LandlordVerificationViewSet, basename='landlord-verification')

urlpatterns = router.urls
