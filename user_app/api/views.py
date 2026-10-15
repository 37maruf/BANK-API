from . import serializers
from user_app import models
from rest_framework.response import Response
from rest_framework import generics, status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser


# POST /api/auth/register/
class RegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'Registration successful.',
            'username': user.username,
            'token': token.key,
        }, status=status.HTTP_201_CREATED)


# POST /api/auth/logout/
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Token deleted Succesfully'})


# GET /api/profile/    -> view my profile
# PATCH /api/profile/  -> update my profile
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.ProfileSerializer
    permission_classes = [IsAuthenticated]

    # always the logged in user, so nobody can see another customer's profile
    def get_object(self):
        models.Customer.objects.get_or_create(user=self.request.user)
        return self.request.user


# GET /api/admin/customers/  -> admin only
class AdminCustomerListView(generics.ListAPIView):
    queryset = User.objects.all().select_related('customer').order_by('id')
    serializer_class = serializers.CustomerListSerializer
    permission_classes = [IsAdminUser]
