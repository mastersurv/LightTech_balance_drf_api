from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import UserBalance, Transaction


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
        help_text="Сумма пополнения в копейках (1 рубль = 100 копеек). Примеры: 100 (1₽), 1000 (10₽), 10000 (100₽)",
        label="Сумма в копейках",
        style={'placeholder': '10000'}
    )

    def validate_amount_kopecks(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        if value > 100000000:
            raise serializers.ValidationError("Максимальная сумма пополнения: 1,000,000 рублей (100,000,000 копеек)")
        return value


class TransferSerializer(serializers.Serializer):
    """
    Сериализатор для перевода денег между пользователями
    """
    recipient_id = serializers.IntegerField(
        help_text="ID пользователя-получателя", 
        label="ID получателя",
        style={'placeholder': '2'}
    )
    amount_kopecks = serializers.IntegerField(
        min_value=1, 
        help_text="Сумма перевода в копейках (1 рубль = 100 копеек). Примеры: 500 (5₽), 1000 (10₽), 5000 (50₽)",
        label="Сумма в копейках",
        style={'placeholder': '5000'}
    )

    def validate_recipient_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким ID не найден")
        return value

    def validate_amount_kopecks(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.id == attrs['recipient_id']:
            raise serializers.ValidationError("Нельзя переводить деньги самому себе")
        return attrs


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