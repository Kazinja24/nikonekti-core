from rest_framework.routers import DefaultRouter
from .views import LeaseViewSet

router = DefaultRouter()
router.register(r'leases', LeaseViewSet, basename='leases')

urlpatterns = router.urls
