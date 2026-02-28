from rest_framework.routers import DefaultRouter

from .views import PropertyReportViewSet, UserBlockViewSet


router = DefaultRouter()
router.register("property-reports", PropertyReportViewSet, basename="property-reports")
router.register("user-blocks", UserBlockViewSet, basename="user-blocks")

urlpatterns = router.urls
