from rest_framework.routers import DefaultRouter

from .views import RentalOfferViewSet

router = DefaultRouter()
router.register("", RentalOfferViewSet, basename="offers")

urlpatterns = router.urls

