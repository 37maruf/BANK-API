# Mini Bank Management System API (Django REST Framework)

Customers can register, create bank accounts, deposit, withdraw, transfer money
and see their transaction history. Admin can see everything.

## Setup
    pip install django djangorestframework
    python manage.py migrate
    python manage.py runserver

API base url: http://127.0.0.1:8000/api/

## Project structure
    bank_project/     project settings and main urls
    user_app/         Customer model, register, login, logout, profile, admin customer list
      api/            serializers.py, views.py, urls.py
    bank/             BankAccount and Transaction models, all money logic
      api/            serializers.py, views.py, urls.py

## Ready admin user (already in db.sqlite3)
    username: admin
    password: admin12345
Customers: create them with the register API.

## Authentication
Register or login to get a token. Send it in every private request:

    Authorization: Token YOUR_TOKEN

## Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/auth/register/ | Register a customer |
| POST | /api/auth/login/ | Login, returns token |
| POST | /api/auth/logout/ | Delete my token |
| GET / PATCH | /api/profile/ | View / update my profile |
| GET | /api/accounts/ | List my accounts |
| POST | /api/accounts/ | Create an account |
| GET | /api/accounts/<id>/ | Account details |
| GET | /api/accounts/<id>/balance/ | Account balance |
| POST | /api/transactions/deposit/ | Deposit |
| POST | /api/transactions/withdraw/ | Withdraw |
| POST | /api/transactions/transfer/ | Transfer |
| GET | /api/transactions/ | My history (paginated, 5 per page, `?page=2`, `?type=DEPOSIT`) |
| GET | /api/admin/customers/ | Admin: all customers |
| GET | /api/admin/accounts/ | Admin: all accounts |
| GET | /api/admin/transactions/ | Admin: all transactions (also supports `?type=`) |

## Request bodies
Register
    {"username": "alice", "email": "alice@mail.com", "password": "alice12345", "password2": "alice12345"}

Login
    {"username": "alice", "password": "alice12345"}

Create account (account_type is "Savings" or "Current")
    {"account_type": "Savings"}

Deposit / Withdraw  ("account" is the account id)
    {"account": 1, "amount": "1000.00"}

Transfer  (receiver is found with the account NUMBER)
    {"from_account": 1, "to_account_number": "5392063037", "amount": "300.00"}

## Business rules covered
- Account number is automatic, 10 digits and unique.
- Balance can never be negative (checked in code and in the database).
- Amount must be greater than zero, otherwise 400.
- Not enough balance: 400 and nothing changes.
- Transfer to the same account: 400.
- Using someone else's account for deposit/withdraw/transfer: 403.
- Seeing someone else's account or balance: 404.
- Deposit, withdraw and transfer use `transaction.atomic()`, so if anything fails, balances are not changed.
- Every successful deposit, withdraw and transfer creates a Transaction record with a unique reference.
- A transfer is saved as one TRANSFER record (sender account + receiver account). Both customers can see it in their history.
- Admin endpoints are only for staff users (customers get 403).

## Test with Postman
1. Import `Mini_Bank_API.postman_collection.json`
2. Run the requests in order from top to bottom. Register and login requests save the token automatically.
3. For the transfer request, copy customer 2's account number into `to_account_number`.

## Run automated tests
    python manage.py test
