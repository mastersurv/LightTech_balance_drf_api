from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from wallet.models import UserBalance, Transaction


class UserBalanceModelTest(TestCase):
    """
    Тесты для модели UserBalance
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
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )

    def test_create_user_balance(self):
        """
        Тест создания баланса пользователя
        """
        balance = UserBalance.objects.create(user=self.user)
        self.assertEqual(balance.balance_kopecks, 0)
        self.assertEqual(balance.user, self.user)
        self.assertIsNotNone(balance.created_at)
        self.assertIsNotNone(balance.updated_at)

    def test_user_balance_str_method(self):
        """
        Тест строкового представления баланса
        """
        balance = UserBalance.objects.create(user=self.user, balance_kopecks=10000)
        expected_str = f"{self.user.username}: {balance.get_balance_rubles()} руб."
        self.assertEqual(str(balance), expected_str)

    def test_get_balance_rubles(self):
        """
        Тест конвертации копеек в рубли
        """
        balance = UserBalance.objects.create(user=self.user, balance_kopecks=12345)
        self.assertEqual(balance.get_balance_rubles(), Decimal('123.45'))

    def test_get_balance_rubles_zero(self):
        """
        Тест конвертации нулевого баланса
        """
        balance = UserBalance.objects.create(user=self.user, balance_kopecks=0)
        self.assertEqual(balance.get_balance_rubles(), Decimal('0'))

    def test_balance_negative_validation(self):
        """
        Тест валидации отрицательного баланса
        """
        balance = UserBalance(user=self.user, balance_kopecks=-100)
        with self.assertRaises(ValidationError):
            balance.full_clean()

    def test_user_one_to_one_constraint(self):
        """
        Тест уникальности баланса для пользователя
        """
        UserBalance.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            UserBalance.objects.create(user=self.user)

    def test_balance_meta_verbose_names(self):
        """
        Тест verbose names модели
        """
        self.assertEqual(UserBalance._meta.verbose_name, "Баланс пользователя")
        self.assertEqual(UserBalance._meta.verbose_name_plural, "Балансы пользователей")

    def test_balance_cascade_delete(self):
        """
        Тест каскадного удаления баланса при удалении пользователя
        """
        balance = UserBalance.objects.create(user=self.user)
        user_id = self.user.id
        balance_id = balance.id
        
        self.user.delete()
        
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertFalse(UserBalance.objects.filter(id=balance_id).exists())


class TransactionModelTest(TestCase):
    """
    Тесты для модели Transaction
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

    def test_create_deposit_transaction(self):
        """
        Тест создания транзакции пополнения
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=10000,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            description="Тестовое пополнение"
        )
        
        self.assertEqual(transaction.to_user, self.user1)
        self.assertIsNone(transaction.from_user)
        self.assertEqual(transaction.amount_kopecks, 10000)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.DEPOSIT)
        self.assertEqual(transaction.description, "Тестовое пополнение")
        self.assertIsNotNone(transaction.created_at)

    def test_create_transfer_transaction(self):
        """
        Тест создания транзакции перевода
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=5000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT,
            description="Тестовый перевод"
        )
        
        self.assertEqual(transaction.from_user, self.user1)
        self.assertEqual(transaction.to_user, self.user2)
        self.assertEqual(transaction.amount_kopecks, 5000)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.TRANSFER_OUT)

    def test_transaction_str_method_with_from_user(self):
        """
        Тест строкового представления транзакции с отправителем
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=12500,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        expected_str = f"{self.user1.username} -> {self.user2.username}: {transaction.get_amount_rubles()} руб."
        self.assertEqual(str(transaction), expected_str)

    def test_transaction_str_method_without_from_user(self):
        """
        Тест строкового представления транзакции без отправителя (пополнение)
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=10000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        expected_str = f"Система -> {self.user1.username}: {transaction.get_amount_rubles()} руб."
        self.assertEqual(str(transaction), expected_str)

    def test_get_amount_rubles(self):
        """
        Тест конвертации суммы транзакции в рубли
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=15678,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        self.assertEqual(transaction.get_amount_rubles(), Decimal('156.78'))

    def test_transaction_type_choices(self):
        """
        Тест типов транзакций
        """
        self.assertEqual(Transaction.TransactionType.DEPOSIT, 'deposit')
        self.assertEqual(Transaction.TransactionType.TRANSFER_OUT, 'transfer_out')
        self.assertEqual(Transaction.TransactionType.TRANSFER_IN, 'transfer_in')

    def test_transaction_meta_ordering(self):
        """
        Тест сортировки транзакций
        """
        transaction1 = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        transaction2 = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=2000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        
        transactions = Transaction.objects.all()
        self.assertEqual(transactions[0], transaction2)
        self.assertEqual(transactions[1], transaction1)

    def test_transaction_meta_verbose_names(self):
        """
        Тест verbose names транзакции
        """
        self.assertEqual(Transaction._meta.verbose_name, "Транзакция")
        self.assertEqual(Transaction._meta.verbose_name_plural, "Транзакции")

    def test_transaction_cascade_delete_from_user(self):
        """
        Тест каскадного удаления транзакций при удалении отправителя
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        transaction_id = transaction.id
        
        self.user1.delete()
        
        self.assertFalse(Transaction.objects.filter(id=transaction_id).exists())

    def test_transaction_cascade_delete_to_user(self):
        """
        Тест каскадного удаления транзакций при удалении получателя
        """
        transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        transaction_id = transaction.id
        
        self.user2.delete()
        
        self.assertFalse(Transaction.objects.filter(id=transaction_id).exists())

    def test_transaction_amount_positive(self):
        """
        Тест положительной суммы транзакции
        """
        transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=1,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        self.assertEqual(transaction.amount_kopecks, 1)

    def test_transaction_related_names(self):
        """
        Тест related_name для связей
        """
        Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=1000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT
        )
        
        self.assertEqual(self.user1.outgoing_transactions.count(), 1)
        self.assertEqual(self.user2.incoming_transactions.count(), 1) 