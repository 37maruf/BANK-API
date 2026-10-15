from rest_framework.authtoken import views
from django.urls import path
from . import views as custom_views

urlpatterns = [
    path('auth/register/', custom_views.RegistrationView.as_view(), name='register'),
    path('auth/login/', views.obtain_auth_token, name='login'),
    path('auth/logout/', custom_views.LogoutView.as_view(), name='logout'),
    path('profile/', custom_views.ProfileView.as_view(), name='profile'),
    path('admin/customers/', custom_views.AdminCustomerListView.as_view(), name='admin-customers'),
]
