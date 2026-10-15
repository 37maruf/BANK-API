import random
import uuid
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


class BankAccount(models.Model):
    SAVINGS = 'Savings'
    CURRENT = 'Current'
    ACCOUNT_TYPES = [
        (SAVINGS, 'Savings'),
        (CURRENT, 'Current'),
    ]

    ACTIVE = 'Active'
    CLOSED = 'Closed'
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (CLOSED, 'Closed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=10, unique=True, editable=False)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # balance can never be negative (also protected in the database)
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name='balance_not_negative'),
        ]

    # make a unique 10 digit account number when the account is created
    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_account_number():
        while True:
            number = str(random.randint(10**9, 10**10 - 1))
            if not BankAccount.objects.filter(account_number=number).exists():
                return number

    def __str__(self):
        return f"{self.account_number} ({self.owner.username})"


class Transaction(models.Model):
    DEPOSIT = 'DEPOSIT'
    WITHDRAW = 'WITHDRAW'
    TRANSFER = 'TRANSFER'
    TRANSACTION_TYPES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAW, 'Withdraw'),
        (TRANSFER, 'Transfer'),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # main account: deposit/withdraw account, or the sender in a transfer
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='transactions')
    # only used for a transfer: the receiver account
    to_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='received_transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='amount_positive'),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} ({self.reference})"
