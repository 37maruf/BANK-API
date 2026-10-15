from rest_framework import serializers
from django.contrib.auth.models import User
from user_app import models


class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']
        extra_kwargs = {'password': {'write_only': True}}

    def save(self):
        username = self.validated_data['username']
        email = self.validated_data['email']
        password1 = self.validated_data['password']
        password2 = self.validated_data['password2']

        if password1 != password2:
            raise serializers.ValidationError({'error': "password doesn't match"})
        if len(password1) < 8:
            raise serializers.ValidationError({'error': "password must be at least 8 characters"})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'error': "email already exists."})

        account = User(
            username=username,
            email=email,
            first_name=self.validated_data.get('first_name', ''),
            last_name=self.validated_data.get('last_name', ''),
        )
        account.set_password(password1)
        account.save()
        models.Customer.objects.create(user=account)
        return account


class ProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='customer.phone_number', required=False,
                                         allow_blank=True, max_length=15)
    address = serializers.CharField(source='customer.address', required=False,
                                    allow_blank=True, max_length=255)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address']
        read_only_fields = ['id', 'username']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("email already exists.")
        return value

    def update(self, instance, validated_data):
        customer_data = validated_data.pop('customer', {})

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        customer, created = models.Customer.objects.get_or_create(user=instance)
        for field, value in customer_data.items():
            setattr(customer, field, value)
        customer.save()
        return instance


# used by admin to see all customers
class CustomerListSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='customer.phone_number', read_only=True, allow_null=True)
    address = serializers.CharField(source='customer.address', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone_number', 'address', 'is_staff', 'date_joined']
