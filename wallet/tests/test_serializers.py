from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from rest_framework import serializers
from decimal import Decimal
from wallet.models import UserBalance, Transaction
from wallet.serializers import BalanceSerializer, DepositSerializer, TransferSerializer, TransactionSerializer


class BalanceSerializerTest(TestCase):
    """
    Тесты для BalanceSerializer
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.balance = UserBalance.objects.create(user=self.user, balance_kopecks=15000)

    def test_balance_serializer_fields(self):
        """
        Тест полей сериализатора баланса
        """
        serializer = BalanceSerializer(instance=self.balance)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['balance_rubles'], 150.0)
        self.assertIn('updated_at', data)

    def test_balance_serializer_get_balance_rubles(self):
        """
        Тест метода get_balance_rubles
        """
        balance_zero = UserBalance.objects.create(
            user=User.objects.create_user(username='user2', password='pass'),
            balance_kopecks=0
        )
        serializer = BalanceSerializer(instance=balance_zero)
        self.assertEqual(serializer.data['balance_rubles'], 0.0)

    def test_balance_serializer_username_read_only(self):
        """
        Тест readonly поля username
        """
        serializer = BalanceSerializer(instance=self.balance)
        self.assertIn('username', serializer.fields)
        self.assertTrue(serializer.fields['username'].read_only)


class DepositSerializerTest(TestCase):
    """
    Тесты для DepositSerializer
    """

    def test_deposit_serializer_valid_data(self):
        """
        Тест валидных данных для пополнения
        """
        data = {'amount_kopecks': 10000}
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['amount_kopecks'], 10000)

    def test_deposit_serializer_zero_amount(self):
        """
        Тест нулевой суммы пополнения
        """
        data = {'amount_kopecks': 0}
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_deposit_serializer_negative_amount(self):
        """
        Тест отрицательной суммы пополнения
        """
        data = {'amount_kopecks': -1000}
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_deposit_serializer_maximum_amount(self):
        """
        Тест превышения максимальной суммы пополнения
        """
        data = {'amount_kopecks': 100000001}
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_deposit_serializer_maximum_allowed_amount(self):
        """
        Тест максимальной разрешенной суммы пополнения
        """
        data = {'amount_kopecks': 100000000}
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_deposit_serializer_missing_field(self):
        """
        Тест отсутствующего поля
        """
        serializer = DepositSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_deposit_serializer_field_attributes(self):
        """
        Тест атрибутов поля amount_kopecks
        """
        serializer = DepositSerializer()
        field = serializer.fields['amount_kopecks']
        self.assertEqual(field.min_value, 1)
        self.assertEqual(field.label, "Сумма в копейках")
        self.assertIn('placeholder', field.style)

    def test_deposit_serializer_validate_amount_kopecks_zero(self):
        """
        Тест валидации нулевой суммы через validate_amount_kopecks
        """
        serializer = DepositSerializer()
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_amount_kopecks(0)


class TransferSerializerTest(TestCase):
    """
    Тесты для TransferSerializer
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
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
        self.factory = RequestFactory()

    def test_transfer_serializer_valid_data(self):
        """
        Тест валидных данных для перевода
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 5000}
        serializer = TransferSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())

    def test_transfer_serializer_nonexistent_recipient(self):
        """
        Тест несуществующего получателя
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        data = {'recipient_id': 99999, 'amount_kopecks': 5000}
        serializer = TransferSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('recipient_id', serializer.errors)

    def test_transfer_serializer_self_transfer(self):
        """
        Тест перевода самому себе
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        data = {'recipient_id': self.user1.id, 'amount_kopecks': 5000}
        serializer = TransferSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_transfer_serializer_zero_amount(self):
        """
        Тест нулевой суммы перевода
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        data = {'recipient_id': self.user2.id, 'amount_kopecks': 0}
        serializer = TransferSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_transfer_serializer_negative_amount(self):
        """
        Тест отрицательной суммы перевода
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        data = {'recipient_id': self.user2.id, 'amount_kopecks': -1000}
        serializer = TransferSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount_kopecks', serializer.errors)

    def test_transfer_serializer_missing_fields(self):
        """
        Тест отсутствующих полей
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        serializer = TransferSerializer(data={}, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('recipient_id', serializer.errors)
        self.assertIn('amount_kopecks', serializer.errors)

    def test_transfer_serializer_field_attributes(self):
        """
        Тест атрибутов полей
        """
        serializer = TransferSerializer()
        
        recipient_field = serializer.fields['recipient_id']
        amount_field = serializer.fields['amount_kopecks']
        
        self.assertEqual(recipient_field.label, "ID получателя")
        self.assertEqual(amount_field.label, "Сумма в копейках")
        self.assertEqual(amount_field.min_value, 1)

    def test_transfer_serializer_validate_amount_kopecks_zero(self):
        """
        Тест валидации нулевой суммы через validate_amount_kopecks
        """
        request = self.factory.post('/')
        request.user = self.user1
        
        serializer = TransferSerializer(context={'request': request})
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_amount_kopecks(0)


class TransactionSerializerTest(TestCase):
    """
    Тесты для TransactionSerializer
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
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

    def test_transaction_serializer_deposit(self):
        """
        Тест сериализации транзакции пополнения
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=10000,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            description="Пополнение баланса"
        )
        
        serializer = TransactionSerializer(instance=transaction)
        data = serializer.data
        
        self.assertEqual(data['from_username'], "Система")
        self.assertEqual(data['to_username'], 'sender')
        self.assertEqual(data['amount_rubles'], 100.0)
        self.assertEqual(data['transaction_type'], 'deposit')
        self.assertEqual(data['transaction_type_display'], 'Пополнение')
        self.assertEqual(data['description'], "Пополнение баланса")

    def test_transaction_serializer_transfer(self):
        """
        Тест сериализации транзакции перевода
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=5000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT,
            description="Перевод денег"
        )
        
        serializer = TransactionSerializer(instance=transaction)
        data = serializer.data
        
        self.assertEqual(data['from_username'], 'sender')
        self.assertEqual(data['to_username'], 'recipient')
        self.assertEqual(data['amount_rubles'], 50.0)
        self.assertEqual(data['transaction_type'], 'transfer_out')

    def test_transaction_serializer_get_from_username_with_user(self):
        """
        Тест метода get_from_username с пользователем
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        
        serializer = TransactionSerializer(instance=transaction)
        self.assertEqual(serializer.get_from_username(transaction), 'sender')

    def test_transaction_serializer_get_from_username_without_user(self):
        """
        Тест метода get_from_username без пользователя (система)
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        
        serializer = TransactionSerializer(instance=transaction)
        self.assertEqual(serializer.get_from_username(transaction), "Система")

    def test_transaction_serializer_get_amount_rubles(self):
        """
        Тест метода get_amount_rubles
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=12345,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        
        serializer = TransactionSerializer(instance=transaction)
        self.assertEqual(serializer.get_amount_rubles(transaction), 123.45)

    def test_transaction_serializer_fields(self):
        """
        Тест наличия всех полей в сериализаторе
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        
        serializer = TransactionSerializer(instance=transaction)
        data = serializer.data
        
        expected_fields = [
            'id', 'from_username', 'to_username', 'amount_rubles',
            'transaction_type', 'transaction_type_display',
            'description', 'created_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_transaction_serializer_read_only_fields(self):
        """
        Тест readonly полей
        """
        serializer = TransactionSerializer()
        
        self.assertTrue(serializer.fields['to_username'].read_only)
        self.assertTrue(serializer.fields['transaction_type_display'].read_only) 