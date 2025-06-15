from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class UserBalance(models.Model):
    """
    Модель для хранения баланса пользователя в копейках
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance')
    balance_kopecks = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Баланс в копейках"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Баланс пользователя"
        verbose_name_plural = "Балансы пользователей"

    def get_balance_rubles(self):
        """
        Возвращает баланс в рублях
        """
        return Decimal(self.balance_kopecks) / 100

    def __str__(self):
        return f"{self.user.username}: {self.get_balance_rubles()} руб."


class Transaction(models.Model):
    """
    Модель для учета всех операций с балансом
    """
    class TransactionType(models.TextChoices):
        DEPOSIT = 'deposit', 'Пополнение'
        TRANSFER_OUT = 'transfer_out', 'Исходящий перевод'
        TRANSFER_IN = 'transfer_in', 'Входящий перевод'

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='outgoing_transactions',
        null=True,
        blank=True,
        help_text="Отправитель (null для пополнения)"
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='incoming_transactions',
        help_text="Получатель"
    )
    amount_kopecks = models.PositiveIntegerField(help_text="Сумма в копейках")
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    description = models.TextField(blank=True, help_text="Описание операции")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-created_at']

    def get_amount_rubles(self):
        """
        Возвращает сумму транзакции в рублях
        """
        return Decimal(self.amount_kopecks) / 100

    def __str__(self):
        from_user = self.from_user.username if self.from_user else "Система"
        return f"{from_user} -> {self.to_user.username}: {self.get_amount_rubles()} руб."
