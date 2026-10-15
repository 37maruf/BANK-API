from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework import status
from bank import models


class BaseTest(APITestCase):

    def make_user(self, username, is_staff=False):
        user = User.objects.create_user(username=username, password='pass12345',
                                        email=f'{username}@mail.com', is_staff=is_staff)
        token = Token.objects.create(user=user)
        return user, token

    def login_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def make_account(self, user, balance='0.00', account_type='Savings'):
        return models.BankAccount.objects.create(
            owner=user, account_type=account_type, balance=Decimal(balance))


class AuthTest(APITestCase):

    def test_register_login_profile(self):
        data = {'username': 'rahim', 'email': 'rahim@mail.com',
                'password': 'secret123', 'password2': 'secret123'}
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)

        response = self.client.post('/api/auth/login/', {'username': 'rahim', 'password': 'secret123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data['token']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.get('/api/profile/')
        self.assertEqual(response.data['username'], 'rahim')

        response = self.client.patch('/api/profile/', {'first_name': 'Rahim', 'phone_number': '01700000000'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Rahim')
        self.assertEqual(response.data['phone_number'], '01700000000')

    def test_register_errors(self):
        data = {'username': 'a', 'email': 'a@mail.com', 'password': 'secret123', 'password2': 'different1'}
        self.assertEqual(self.client.post('/api/auth/register/', data).status_code, 400)
        data['password2'] = 'secret123'
        self.assertEqual(self.client.post('/api/auth/register/', data).status_code, 201)
        # same email again
        data['username'] = 'b'
        self.assertEqual(self.client.post('/api/auth/register/', data).status_code, 400)

    def test_private_endpoints_need_login(self):
        for url in ['/api/profile/', '/api/accounts/', '/api/transactions/']:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)


class AccountTest(BaseTest):

    def setUp(self):
        self.user1, self.token1 = self.make_user('user1')
        self.user2, self.token2 = self.make_user('user2')

    def test_create_account_unique_number(self):
        self.login_as(self.token1)
        r1 = self.client.post('/api/accounts/', {'account_type': 'Savings'})
        r2 = self.client.post('/api/accounts/', {'account_type': 'Current'})
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.data['account_number'], r2.data['account_number'])
        self.assertEqual(r1.data['balance'], '0.00')

    def test_invalid_account_type(self):
        self.login_as(self.token1)
        response = self.client.post('/api/accounts/', {'account_type': 'Gold'})
        self.assertEqual(response.status_code, 400)

    def test_customer_cannot_see_other_account(self):
        other = self.make_account(self.user2, '500.00')
        self.login_as(self.token1)
        self.assertEqual(self.client.get(f'/api/accounts/{other.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/accounts/{other.id}/balance/').status_code, 404)
        self.assertEqual(self.client.get('/api/accounts/').data['count'], 0)

    def test_balance(self):
        acc = self.make_account(self.user1, '250.50')
        self.login_as(self.token1)
        response = self.client.get(f'/api/accounts/{acc.id}/balance/')
        self.assertEqual(response.data['balance'], '250.50')


class MoneyTest(BaseTest):

    def setUp(self):
        self.user1, self.token1 = self.make_user('user1')
        self.user2, self.token2 = self.make_user('user2')
        self.acc1 = self.make_account(self.user1, '1000.00')
        self.acc2 = self.make_account(self.user2, '200.00', 'Current')
        self.login_as(self.token1)

    def balance(self, account):
        account.refresh_from_db()
        return account.balance

    def test_deposit(self):
        r = self.client.post('/api/transactions/deposit/', {'account': self.acc1.id, 'amount': '100.50'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.balance(self.acc1), Decimal('1100.50'))
        self.assertEqual(models.Transaction.objects.filter(transaction_type='DEPOSIT').count(), 1)

    def test_withdraw(self):
        r = self.client.post('/api/transactions/withdraw/', {'account': self.acc1.id, 'amount': '400'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.balance(self.acc1), Decimal('600.00'))
        self.assertEqual(models.Transaction.objects.filter(transaction_type='WITHDRAW').count(), 1)

    def test_zero_and_negative_amount_rejected(self):
        for url, key in [('deposit', 'account'), ('withdraw', 'account')]:
            for amount in ['0', '-10', '0.00']:
                r = self.client.post(f'/api/transactions/{url}/', {key: self.acc1.id, 'amount': amount})
                self.assertEqual(r.status_code, 400, (url, amount))
        r = self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': self.acc2.account_number, 'amount': '-5'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.balance(self.acc1), Decimal('1000.00'))
        self.assertEqual(models.Transaction.objects.count(), 0)

    def test_insufficient_balance_fails_and_balance_unchanged(self):
        r = self.client.post('/api/transactions/withdraw/', {'account': self.acc1.id, 'amount': '5000'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.balance(self.acc1), Decimal('1000.00'))
        r = self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': self.acc2.account_number, 'amount': '5000'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.balance(self.acc1), Decimal('1000.00'))
        self.assertEqual(self.balance(self.acc2), Decimal('200.00'))
        self.assertEqual(models.Transaction.objects.count(), 0)

    def test_cannot_use_someone_elses_account(self):
        for url, data in [
            ('deposit', {'account': self.acc2.id, 'amount': '10'}),
            ('withdraw', {'account': self.acc2.id, 'amount': '10'}),
            ('transfer', {'from_account': self.acc2.id,
                          'to_account_number': self.acc1.account_number, 'amount': '10'}),
        ]:
            r = self.client.post(f'/api/transactions/{url}/', data)
            self.assertEqual(r.status_code, 403, url)
        self.assertEqual(self.balance(self.acc2), Decimal('200.00'))

    def test_transfer(self):
        r = self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': self.acc2.account_number, 'amount': '300.00'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.balance(self.acc1), Decimal('700.00'))
        self.assertEqual(self.balance(self.acc2), Decimal('500.00'))
        self.assertEqual(models.Transaction.objects.filter(transaction_type='TRANSFER').count(), 1)

    def test_transfer_same_account(self):
        r = self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': self.acc1.account_number, 'amount': '10'})
        self.assertEqual(r.status_code, 400)

    def test_transfer_unknown_receiver(self):
        r = self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': '0000000000', 'amount': '10'})
        self.assertEqual(r.status_code, 404)


class HistoryTest(BaseTest):

    def setUp(self):
        self.user1, self.token1 = self.make_user('user1')
        self.user2, self.token2 = self.make_user('user2')
        self.user3, self.token3 = self.make_user('user3')
        self.acc1 = self.make_account(self.user1, '1000.00')
        self.acc2 = self.make_account(self.user2, '0.00')
        self.acc3 = self.make_account(self.user3, '0.00')
        self.login_as(self.token1)
        for i in range(4):
            self.client.post('/api/transactions/deposit/', {'account': self.acc1.id, 'amount': '10'})
        for i in range(3):
            self.client.post('/api/transactions/withdraw/', {'account': self.acc1.id, 'amount': '5'})
        self.client.post('/api/transactions/transfer/', {
            'from_account': self.acc1.id, 'to_account_number': self.acc2.account_number, 'amount': '20'})
        # user3 has own deposit - user1 must never see it
        self.login_as(self.token3)
        self.client.post('/api/transactions/deposit/', {'account': self.acc3.id, 'amount': '999'})

    def test_history_is_private_and_paginated(self):
        self.login_as(self.token1)
        r = self.client.get('/api/transactions/')
        self.assertEqual(r.data['count'], 8)
        self.assertEqual(len(r.data['results']), 5)
        self.assertIsNotNone(r.data['next'])
        page2 = self.client.get('/api/transactions/?page=2')
        self.assertEqual(len(page2.data['results']), 3)

        self.login_as(self.token3)
        self.assertEqual(self.client.get('/api/transactions/').data['count'], 1)

    def test_filter_by_type(self):
        self.login_as(self.token1)
        self.assertEqual(self.client.get('/api/transactions/?type=DEPOSIT').data['count'], 4)
        self.assertEqual(self.client.get('/api/transactions/?type=withdraw').data['count'], 3)
        self.assertEqual(self.client.get('/api/transactions/?type=TRANSFER').data['count'], 1)
        self.assertEqual(self.client.get('/api/transactions/?type=abc').status_code, 400)

    def test_receiver_sees_incoming_transfer(self):
        self.login_as(self.token2)
        r = self.client.get('/api/transactions/')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['transaction_type'], 'TRANSFER')

    def test_transaction_fields(self):
        self.login_as(self.token1)
        item = self.client.get('/api/transactions/?type=TRANSFER').data['results'][0]
        for key in ['transaction_type', 'amount', 'created_at', 'account_number', 'to_account_number', 'reference']:
            self.assertIn(key, item)


class AdminTest(BaseTest):

    def setUp(self):
        self.user1, self.token1 = self.make_user('user1')
        self.admin, self.admin_token = self.make_user('boss', is_staff=True)
        self.acc1 = self.make_account(self.user1, '100.00')

    def test_customer_cannot_use_admin_endpoints(self):
        self.login_as(self.token1)
        for url in ['/api/admin/customers/', '/api/admin/accounts/', '/api/admin/transactions/']:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_everything(self):
        self.login_as(self.token1)
        self.client.post('/api/transactions/deposit/', {'account': self.acc1.id, 'amount': '10'})
        self.login_as(self.admin_token)
        self.assertEqual(self.client.get('/api/admin/customers/').data['count'], 2)
        self.assertEqual(self.client.get('/api/admin/accounts/').data['count'], 1)
        self.assertEqual(self.client.get('/api/admin/transactions/').data['count'], 1)
