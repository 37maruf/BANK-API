from bank import models
from . import serializers
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers as drf_serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser


# GET  /api/accounts/  -> list my accounts
# POST /api/accounts/  -> create a new account
class AccountListCreateView(generics.ListCreateAPIView):
    serializer_class = serializers.BankAccountSerializer
    permission_classes = [IsAuthenticated]

    # customer sees only their own accounts
    def get_queryset(self):
        return models.BankAccount.objects.filter(owner=self.request.user).order_by('id')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# GET /api/accounts/<id>/  -> account details (only my account, otherwise 404)
class AccountDetailView(generics.RetrieveAPIView):
    serializer_class = serializers.BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return models.BankAccount.objects.filter(owner=self.request.user)


# GET /api/accounts/<id>/balance/
class AccountBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        account = get_object_or_404(models.BankAccount, pk=pk, owner=request.user)
        return Response({
            'account_number': account.account_number,
            'balance': str(account.balance),
        })


# Deposit, Withdraw and Transfer views are almost the same,
# so they share this base class.
class BaseMoneyView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None
    success_message = ''

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()

        return Response({
            'message': self.success_message,
            'transaction': serializers.TransactionSerializer(transaction).data,
            'balance': str(transaction.account.balance),
        }, status=status.HTTP_201_CREATED)


# POST /api/transactions/deposit/
class DepositView(BaseMoneyView):
    serializer_class = serializers.DepositSerializer
    success_message = 'Deposit successful.'


# POST /api/transactions/withdraw/
class WithdrawView(BaseMoneyView):
    serializer_class = serializers.WithdrawSerializer
    success_message = 'Withdrawal successful.'


# POST /api/transactions/transfer/
class TransferView(BaseMoneyView):
    serializer_class = serializers.TransferSerializer
    success_message = 'Transfer successful.'


# GET /api/transactions/?type=DEPOSIT   -> my transaction history (paginated)
class TransactionListView(generics.ListAPIView):
    serializer_class = serializers.TransactionSerializer
    permission_classes = [IsAuthenticated]

    # customer sees transactions where one of their accounts is involved
    def get_base_queryset(self):
        user = self.request.user
        return models.Transaction.objects.filter(
            Q(account__owner=user) | Q(to_account__owner=user))

    def get_queryset(self):
        queryset = self.get_base_queryset().select_related('account', 'to_account')

        # filter by transaction type
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            transaction_type = transaction_type.upper()
            valid_types = [t[0] for t in models.Transaction.TRANSACTION_TYPES]
            if transaction_type not in valid_types:
                raise drf_serializers.ValidationError(
                    {'type': f"Invalid type. Choose from: {', '.join(valid_types)}"})
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset.order_by('-created_at', '-id')


# ---------------- Admin only ----------------

# GET /api/admin/accounts/
class AdminAccountListView(generics.ListAPIView):
    queryset = models.BankAccount.objects.all().select_related('owner').order_by('id')
    serializer_class = serializers.AdminBankAccountSerializer
    permission_classes = [IsAdminUser]


# GET /api/admin/transactions/
class AdminTransactionListView(TransactionListView):
    permission_classes = [IsAdminUser]

    def get_base_queryset(self):
        return models.Transaction.objects.all()
