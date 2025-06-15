from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from wallet.models import UserBalance, Transaction


class BaseAPITestCase(TestCase):
    """
    Базовый класс для API тестов
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user1)


class GetBalanceViewTest(BaseAPITestCase):
    """
    Тесты для view получения баланса
    """

    def test_get_balance_creates_new_balance(self):
        """
        Тест создания нового баланса при первом запросе
        """
        url = reverse('get_balance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance_rubles'], 0.0)
        self.assertEqual(response.data['username'], 'user1')
        
        self.assertTrue(UserBalance.objects.filter(user=self.user1).exists())

    def test_get_balance_existing_balance(self):
        """
        Тест получения существующего баланса
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=15000)
        
        url = reverse('get_balance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance_rubles'], 150.0)

    def test_get_balance_unauthenticated(self):
        """
        Тест получения баланса неаутентифицированным пользователем
        """
        self.client.force_authenticate(user=None)
        url = reverse('get_balance')
        response = self.client.get(url)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_balance_method_not_allowed(self):
        """
        Тест недопустимого HTTP метода
        """
        url = reverse('get_balance')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DepositBalanceViewTest(BaseAPITestCase):
    """
    Тесты для view пополнения баланса
    """

    def test_deposit_balance_get_method(self):
        """
        Тест GET запроса к endpoint пополнения (показ формы)
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=5000)
        
        url = reverse('deposit_balance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('description', response.data)
        self.assertIn('current_balance_rubles', response.data)
        self.assertIn('example', response.data)
        self.assertIn('form_fields', response.data)
        self.assertEqual(response.data['current_balance_rubles'], 50.0)

    def test_deposit_balance_get_method_new_user(self):
        """
        Тест GET запроса для нового пользователя
        """
        url = reverse('deposit_balance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_balance_rubles'], 0.0)

    def test_deposit_balance_valid_post(self):
        """
        Тест успешного пополнения баланса
        """
        url = reverse('deposit_balance')
        data = {'amount_kopecks': 10000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['deposited_amount_rubles'], 100.0)
        self.assertEqual(response.data['new_balance_rubles'], 100.0)
        
        balance = UserBalance.objects.get(user=self.user1)
        self.assertEqual(balance.balance_kopecks, 10000)
        
        transaction = Transaction.objects.get(to_user=self.user1)
        self.assertEqual(transaction.amount_kopecks, 10000)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.DEPOSIT)

    def test_deposit_balance_existing_balance(self):
        """
        Тест пополнения существующего баланса
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=5000)
        
        url = reverse('deposit_balance')
        data = {'amount_kopecks': 10000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['new_balance_rubles'], 150.0)
        
        balance = UserBalance.objects.get(user=self.user1)
        self.assertEqual(balance.balance_kopecks, 15000)

    def test_deposit_balance_invalid_amount(self):
        """
        Тест пополнения с невалидной суммой
        """
        url = reverse('deposit_balance')
        data = {'amount_kopecks': -1000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_kopecks', response.data)

    def test_deposit_balance_missing_amount(self):
        """
        Тест пополнения без указания суммы
        """
        url = reverse('deposit_balance')
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_kopecks', response.data)

    def test_deposit_balance_unauthenticated(self):
        """
        Тест пополнения неаутентифицированным пользователем
        """
        self.client.force_authenticate(user=None)
        url = reverse('deposit_balance')
        data = {'amount_kopecks': 10000}
        response = self.client.post(url, data)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class TransferMoneyViewTest(TransactionTestCase):
    """
    Тесты для view перевода денег
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='third',
            email='third@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user1)

    def test_transfer_money_get_method(self):
        """
        Тест GET запроса к endpoint перевода (показ формы)
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=10000)
        
        url = reverse('transfer_money')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('description', response.data)
        self.assertIn('current_balance_rubles', response.data)
        self.assertIn('sample_recipients', response.data)
        self.assertIn('form_fields', response.data)
        self.assertEqual(response.data['current_balance_rubles'], 100.0)

    def test_transfer_money_successful(self):
        """
        Тест успешного перевода денег
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=10000)
        
        url = reverse('transfer_money')
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 5000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['recipient_username'], 'recipient')
        self.assertEqual(response.data['amount_rubles'], 50.0)
        self.assertEqual(response.data['new_balance_rubles'], 50.0)
        
        sender_balance = UserBalance.objects.get(user=self.user1)
        recipient_balance = UserBalance.objects.get(user=self.user2)
        self.assertEqual(sender_balance.balance_kopecks, 5000)
        self.assertEqual(recipient_balance.balance_kopecks, 5000)
        
        self.assertEqual(Transaction.objects.count(), 2)

    def test_transfer_money_insufficient_funds(self):
        """
        Тест перевода при недостатке средств
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=1000)
        
        url = reverse('transfer_money')
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 5000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_transfer_money_to_self(self):
        """
        Тест перевода самому себе
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=10000)
        
        url = reverse('transfer_money')
        data = {'recipient_id': self.user1.id, 'amount_kopecks': 5000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_money_nonexistent_recipient(self):
        """
        Тест перевода несуществующему пользователю
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=10000)
        
        url = reverse('transfer_money')
        data = {'recipient_id': 99999, 'amount_kopecks': 5000}
        response = self.client.post(url, data)
        
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST])

    def test_transfer_money_creates_both_transactions(self):
        """
        Тест создания обеих транзакций при переводе
        """
        UserBalance.objects.create(user=self.user1, balance_kopecks=10000)
        
        url = reverse('transfer_money')
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 3000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        outgoing = Transaction.objects.get(
            from_user=self.user1,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        incoming = Transaction.objects.get(
            to_user=self.user2,
            transaction_type=Transaction.TransactionType.TRANSFER_IN
        )
        
        self.assertEqual(outgoing.amount_kopecks, 3000)
        self.assertEqual(incoming.amount_kopecks, 3000)

    def test_transfer_money_zero_balance_sender(self):
        """
        Тест перевода при нулевом балансе отправителя
        """
        url = reverse('transfer_money')
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 1000}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class GetTransactionsViewTest(BaseAPITestCase):
    """
    Тесты для view получения транзакций
    """

    def test_get_transactions_empty(self):
        """
        Тест получения пустого списка транзакций
        """
        url = reverse('get_transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_transactions_with_data(self):
        """
        Тест получения списка транзакций
        """
        Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=10000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=5000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        
        url = reverse('get_transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_transactions_ordering(self):
        """
        Тест сортировки транзакций по дате
        """
        t1 = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        t2 = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=2000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        
        url = reverse('get_transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], t2.id)
        self.assertEqual(response.data[1]['id'], t1.id)

    def test_get_transactions_filters_by_user(self):
        """
        Тест фильтрации транзакций по пользователю
        """
        Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        Transaction.objects.create(
            to_user=self.user2,
            amount_kopecks=2000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        
        url = reverse('get_transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['amount_rubles'], 10.0)

    def test_get_transactions_method_not_allowed(self):
        """
        Тест недопустимого HTTP метода
        """
        url = reverse('get_transactions')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_transactions_includes_incoming_and_outgoing(self):
        """
        Тест включения входящих и исходящих транзакций
        """
        Transaction.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_IN
        )
        Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=2000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        
        url = reverse('get_transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) 