from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import logging


logger = logging.getLogger('wallet')


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

    def save(self, *args, **kwargs):
        """
        Переопределение метода save для логирования изменений
        """
        is_new = self.pk is None
        old_balance = None
        
        if not is_new:
            try:
                old_instance = UserBalance.objects.get(pk=self.pk)
                old_balance = old_instance.balance_kopecks
            except UserBalance.DoesNotExist:
                old_balance = 0
        
        super().save(*args, **kwargs)
        
        if is_new:
            logger.info(f"Создан новый баланс для пользователя {self.user.username}: {self.get_balance_rubles()} руб")
        elif old_balance is not None and old_balance != self.balance_kopecks:
            old_balance_rubles = float(old_balance / 100)
            new_balance_rubles = float(self.get_balance_rubles())
            logger.info(
                f"Обновлен баланс пользователя {self.user.username}: "
                f"{old_balance_rubles} -> {new_balance_rubles} руб"
            )

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

    def save(self, *args, **kwargs):
        """
        Переопределение метода save для логирования создания транзакций
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            from_user_name = self.from_user.username if self.from_user else "Система"
            logger.info(
                f"Создана транзакция {self.transaction_type}: {from_user_name} -> {self.to_user.username} "
                f"({self.get_amount_rubles()} руб) [ID: {self.pk}]"
            )

    def __str__(self):
        from_user = self.from_user.username if self.from_user else "Система"
        return f"{from_user} -> {self.to_user.username}: {self.get_amount_rubles()} руб."
