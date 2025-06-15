from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import UserBalance, Transaction
import logging


logger = logging.getLogger('wallet')
security_logger = logging.getLogger('wallet.security')


class BalanceSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения баланса пользователя
    """
    balance_rubles = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserBalance
        fields = ['username', 'balance_rubles', 'updated_at']

    def get_balance_rubles(self, obj):
        return float(obj.get_balance_rubles())


class DepositSerializer(serializers.Serializer):
    """
    Сериализатор для пополнения баланса
    """
    amount_kopecks = serializers.IntegerField(
        min_value=1,
        max_value=100000000,
        help_text="Сумма пополнения в копейках (1 рубль = 100 копеек)",
        label="Сумма в копейках"
    )

    def validate_amount_kopecks(self, value):
        """
        Валидация суммы пополнения с логированием
        """
        if value <= 0:
            logger.warning(f"Попытка пополнения на отрицательную или нулевую сумму: {value}")
            security_logger.warning(f"NEGATIVE_DEPOSIT_ATTEMPT | amount={value}")
            raise serializers.ValidationError("Сумма пополнения должна быть положительной")
        
        if value > 100000000:
            logger.warning(f"Попытка пополнения на очень большую сумму: {value} копеек")
            security_logger.warning(f"LARGE_DEPOSIT_ATTEMPT | amount={value}")
            raise serializers.ValidationError("Сумма пополнения слишком велика")
        
        return value


class TransferSerializer(serializers.Serializer):
    """
    Сериализатор для перевода денег между пользователями
    """
    recipient_id = serializers.IntegerField(
        help_text="ID пользователя-получателя",
        label="ID получателя"
    )
    amount_kopecks = serializers.IntegerField(
        min_value=1,
        max_value=100000000,
        help_text="Сумма перевода в копейках (1 рубль = 100 копеек)",
        label="Сумма в копейках"
    )

    def validate_recipient_id(self, value):
        """
        Валидация получателя с логированием
        """
        request = self.context.get('request')
        
        try:
            recipient = User.objects.get(id=value)
        except User.DoesNotExist:
            logger.warning(f"Попытка перевода несуществующему пользователю (ID: {value})")
            security_logger.warning(f"TRANSFER_TO_NONEXISTENT | recipient_id={value}")
            raise serializers.ValidationError("Пользователь с указанным ID не найден")
        
        if request and request.user.is_authenticated and recipient.id == request.user.id:
            logger.warning(f"Попытка перевода самому себе: {request.user.username}")
            security_logger.warning(f"SELF_TRANSFER_VALIDATION | user={request.user.username}")
            raise serializers.ValidationError("Нельзя переводить деньги самому себе")
        
        return value

    def validate_amount_kopecks(self, value):
        """
        Валидация суммы перевода с логированием
        """
        if value <= 0:
            logger.warning(f"Попытка перевода отрицательной или нулевой суммы: {value}")
            security_logger.warning(f"NEGATIVE_TRANSFER_ATTEMPT | amount={value}")
            raise serializers.ValidationError("Сумма перевода должна быть положительной")
        
        if value > 100000000:
            logger.warning(f"Попытка перевода очень большой суммы: {value} копеек")
            security_logger.warning(f"LARGE_TRANSFER_ATTEMPT | amount={value}")
            raise serializers.ValidationError("Сумма перевода слишком велика")
        
        return value

    def validate(self, data):
        """
        Общая валидация с проверкой баланса
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_balance = UserBalance.objects.get(user=request.user)
                if user_balance.balance_kopecks < data['amount_kopecks']:
                    logger.warning(
                        f"Попытка перевода при недостатке средств: пользователь {request.user.username}, "
                        f"нужно {data['amount_kopecks']}, есть {user_balance.balance_kopecks}"
                    )
                    security_logger.warning(
                        f"INSUFFICIENT_FUNDS_VALIDATION | user={request.user.username} | "
                        f"required={data['amount_kopecks']} | available={user_balance.balance_kopecks}"
                    )
                    raise serializers.ValidationError("Недостаточно средств на балансе")
            except UserBalance.DoesNotExist:
                logger.warning(f"Попытка перевода пользователем без баланса: {request.user.username}")
                security_logger.warning(f"NO_BALANCE_TRANSFER | user={request.user.username}")
                raise serializers.ValidationError("У вас нет баланса для перевода")
        
        return data


class TransactionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения транзакций
    """
    from_username = serializers.SerializerMethodField()
    to_username = serializers.CharField(source='to_user.username', read_only=True)
    amount_rubles = serializers.SerializerMethodField()
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'from_username', 'to_username', 'amount_rubles',
            'transaction_type', 'transaction_type_display',
            'description', 'created_at'
        ]

    def get_from_username(self, obj):
        return obj.from_user.username if obj.from_user else "Система"

    def get_amount_rubles(self, obj):
        return float(obj.get_amount_rubles()) 