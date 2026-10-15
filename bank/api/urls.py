from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.AccountListCreateView.as_view(), name='account-list'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('accounts/<int:pk>/balance/', views.AccountBalanceView.as_view(), name='account-balance'),

    path('transactions/deposit/', views.DepositView.as_view(), name='deposit'),
    path('transactions/withdraw/', views.WithdrawView.as_view(), name='withdraw'),
    path('transactions/transfer/', views.TransferView.as_view(), name='transfer'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction-list'),

    # admin only
    path('admin/accounts/', views.AdminAccountListView.as_view(), name='admin-accounts'),
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin-transactions'),
]
