"""
URL configuration for nikonekti_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from users.views import LoginView, RegisterView, ProfileView
from properties.views import PropertyViewSet
from viewings.views import ViewingViewSet
from leases.views import LeaseViewSet
from payments.views import PaymentViewSet
from verification.views import LandlordVerificationViewSet
from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='properties')
router.register(r'viewings', ViewingViewSet, basename='viewings')
router.register(r'leases', LeaseViewSet, basename='leases')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'landlord-verifications', LandlordVerificationViewSet, basename='landlord-verifications')


urlpatterns = [
    path('admin/', admin.site.urls),

    path('users/', include('users.urls')),
    path('api/users/', include('users.urls')),
    path('api/applications/', include('applications.urls')),
    path('api/offers/', include('offers.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/audit/', include('audit.urls')),
    path('api/chat/', include('messages.urls')),
    path('api/reports/', include('reports.urls')),



    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema')),


    path('api/login/', LoginView.as_view(), name='login'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/profile/', ProfileView.as_view(), name='auth-profile'),
    path('login/', LoginView.as_view()),
    path('api/', include(router.urls)),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
