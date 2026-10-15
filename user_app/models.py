from django.db import models
from django.contrib.auth.models import User


# Extra customer information. Login data (username, email, password)
# stays in Django's built-in User model.
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.username
