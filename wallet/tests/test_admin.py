from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from wallet.models import UserBalance, Transaction
from wallet.admin import UserBalanceAdmin, TransactionAdmin


class MockRequest:
    """
    Мок объект для request
    """
    pass


class UserBalanceAdminTest(TestCase):
    """
    Тесты для UserBalanceAdmin
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
        self.site = AdminSite()
        self.admin = UserBalanceAdmin(UserBalance, self.site)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.balance = UserBalance.objects.create(
            user=self.user,
            balance_kopecks=12345
        )

    def test_list_display_fields(self):
        """
        Тест полей отображения в списке
        """
        expected_fields = ['user', 'balance_kopecks', 'get_balance_rubles', 'updated_at']
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """
        Тест полей фильтрации
        """
        expected_fields = ['created_at', 'updated_at']
        self.assertEqual(self.admin.list_filter, expected_fields)

    def test_search_fields(self):
        """
        Тест полей поиска
        """
        expected_fields = ['user__username', 'user__email']
        self.assertEqual(self.admin.search_fields, expected_fields)

    def test_readonly_fields(self):
        """
        Тест полей только для чтения
        """
        expected_fields = ['created_at', 'updated_at']
        self.assertEqual(self.admin.readonly_fields, expected_fields)

    def test_get_balance_rubles_method(self):
        """
        Тест метода get_balance_rubles
        """
        result = self.admin.get_balance_rubles(self.balance)
        self.assertEqual(result, "123.45 руб.")

    def test_get_balance_rubles_short_description(self):
        """
        Тест короткого описания метода get_balance_rubles
        """
        self.assertEqual(
            self.admin.get_balance_rubles.short_description,
            'Баланс в рублях'
        )

    def test_get_balance_rubles_zero_balance(self):
        """
        Тест метода get_balance_rubles с нулевым балансом
        """
        zero_balance = UserBalance.objects.create(
            user=User.objects.create_user(username='zero', password='pass'),
            balance_kopecks=0
        )
        result = self.admin.get_balance_rubles(zero_balance)
        self.assertEqual(result, "0 руб.")


class TransactionAdminTest(TestCase):
    """
    Тесты для TransactionAdmin
    """

    def setUp(self):
        """
        Настройка тестовых данных
        """
        self.site = AdminSite()
        self.admin = TransactionAdmin(Transaction, self.site)
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
        self.transaction = Transaction.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            amount_kopecks=25000,
            transaction_type=Transaction.TransactionType.TRANSFER_OUT,
            description="Тестовый перевод"
        )

    def test_list_display_fields(self):
        """
        Тест полей отображения в списке
        """
        expected_fields = [
            'id', 'from_user', 'to_user', 'amount_kopecks', 
            'get_amount_rubles', 'transaction_type', 'created_at'
        ]
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """
        Тест полей фильтрации
        """
        expected_fields = ['transaction_type', 'created_at']
        self.assertEqual(self.admin.list_filter, expected_fields)

    def test_search_fields(self):
        """
        Тест полей поиска
        """
        expected_fields = ['from_user__username', 'to_user__username', 'description']
        self.assertEqual(self.admin.search_fields, expected_fields)

    def test_readonly_fields(self):
        """
        Тест полей только для чтения
        """
        expected_fields = ['created_at']
        self.assertEqual(self.admin.readonly_fields, expected_fields)

    def test_get_amount_rubles_method(self):
        """
        Тест метода get_amount_rubles
        """
        result = self.admin.get_amount_rubles(self.transaction)
        self.assertEqual(result, f"{self.transaction.get_amount_rubles()} руб.")

    def test_get_amount_rubles_short_description(self):
        """
        Тест короткого описания метода get_amount_rubles
        """
        self.assertEqual(
            self.admin.get_amount_rubles.short_description,
            'Сумма в рублях'
        )

    def test_get_amount_rubles_deposit_transaction(self):
        """
        Тест метода get_amount_rubles для транзакции пополнения
        """
        deposit_transaction = Transaction.objects.create(
            to_user=self.user1,
            amount_kopecks=100000,
            transaction_type=Transaction.TransactionType.DEPOSIT
        )
        result = self.admin.get_amount_rubles(deposit_transaction)
        self.assertEqual(result, f"{deposit_transaction.get_amount_rubles()} руб.")

    def test_admin_registration(self):
        """
        Тест регистрации моделей в админке
        """
        from django.contrib import admin
        self.assertIn(UserBalance, admin.site._registry)
        self.assertIn(Transaction, admin.site._registry)
        self.assertIsInstance(admin.site._registry[UserBalance], UserBalanceAdmin)
        self.assertIsInstance(admin.site._registry[Transaction], TransactionAdmin) 