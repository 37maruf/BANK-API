from django.db import transaction
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from bank import models


class BankAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.BankAccount
        fields = ['id', 'account_number', 'account_type', 'balance', 'status', 'created_at']
        # customer can only choose the account type, everything else is automatic
        read_only_fields = ['id', 'account_number', 'balance', 'status', 'created_at']


# admin can also see who owns the account
class AdminBankAccountSerializer(BankAccountSerializer):
    owner = serializers.CharField(source='owner.username', read_only=True)

    class Meta(BankAccountSerializer.Meta):
        fields = ['id', 'owner'] + BankAccountSerializer.Meta.fields[1:]


class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    to_account_number = serializers.CharField(source='to_account.account_number',
                                              read_only=True, allow_null=True)

    class Meta:
        model = models.Transaction
        fields = ['id', 'reference', 'transaction_type', 'amount',
                  'account_number', 'to_account_number', 'created_at']


# ---------------- Deposit / Withdraw / Transfer ----------------

class BaseMoneySerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    # amount must be positive
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    # find the account and make sure it belongs to the logged in customer
    def get_own_account(self, account_id):
        user = self.context['request'].user
        try:
            account = models.BankAccount.objects.get(pk=account_id)
        except models.BankAccount.DoesNotExist:
            raise NotFound("Account not found.")

        if account.owner != user:
            raise PermissionDenied("You can only use your own account.")
        if account.status != models.BankAccount.ACTIVE:
            raise serializers.ValidationError("This account is not active.")
        return account


class DepositSerializer(BaseMoneySerializer):
    account = serializers.IntegerField()

    def validate_account(self, value):
        return self.get_own_account(value)

    def save(self):
        amount = self.validated_data['amount']

        # atomic: everything is saved, or nothing is saved
        with transaction.atomic():
            account = models.BankAccount.objects.select_for_update().get(
                pk=self.validated_data['account'].pk)
            account.balance += amount
            account.save()
            return models.Transaction.objects.create(
                transaction_type=models.Transaction.DEPOSIT,
                account=account,
                amount=amount,
            )


class WithdrawSerializer(BaseMoneySerializer):
    account = serializers.IntegerField()

    def validate_account(self, value):
        return self.get_own_account(value)

    def save(self):
        amount = self.validated_data['amount']

        with transaction.atomic():
            account = models.BankAccount.objects.select_for_update().get(
                pk=self.validated_data['account'].pk)

            if account.balance < amount:
                raise serializers.ValidationError({'amount': ["Insufficient balance."]})

            account.balance -= amount
            account.save()
            return models.Transaction.objects.create(
                transaction_type=models.Transaction.WITHDRAW,
                account=account,
                amount=amount,
            )


class TransferSerializer(BaseMoneySerializer):
    from_account = serializers.IntegerField()
    to_account_number = serializers.CharField(max_length=10)

    def validate_from_account(self, value):
        return self.get_own_account(value)

    def validate_to_account_number(self, value):
        try:
            receiver = models.BankAccount.objects.get(account_number=value)
        except models.BankAccount.DoesNotExist:
            raise NotFound("Receiver account not found.")
        if receiver.status != models.BankAccount.ACTIVE:
            raise serializers.ValidationError("Receiver account is not active.")
        return receiver

    def validate(self, attrs):
        if attrs['from_account'].pk == attrs['to_account_number'].pk:
            raise serializers.ValidationError("You cannot transfer money to the same account.")
        return attrs

    def save(self):
        amount = self.validated_data['amount']
        sender_id = self.validated_data['from_account'].pk
        receiver_id = self.validated_data['to_account_number'].pk

        with transaction.atomic():
            # lock both accounts (always in the same order to avoid deadlock)
            locked = {a.pk: a for a in models.BankAccount.objects.select_for_update()
                      .filter(pk__in=[sender_id, receiver_id]).order_by('pk')}
            sender = locked[sender_id]
            receiver = locked[receiver_id]

            if sender.balance < amount:
                raise serializers.ValidationError({'amount': ["Insufficient balance."]})

            sender.balance -= amount
            receiver.balance += amount
            sender.save()
            receiver.save()

            return models.Transaction.objects.create(
                transaction_type=models.Transaction.TRANSFER,
                account=sender,
                to_account=receiver,
                amount=amount,
            )
