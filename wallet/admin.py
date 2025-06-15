from django.contrib import admin
from .models import UserBalance, Transaction


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance_kopecks', 'get_balance_rubles', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_balance_rubles(self, obj):
        return f"{obj.get_balance_rubles()} руб."
    get_balance_rubles.short_description = 'Баланс в рублях'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'from_user', 'to_user', 'amount_kopecks', 'get_amount_rubles', 'transaction_type', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['from_user__username', 'to_user__username', 'description']
    readonly_fields = ['created_at']
    
    def get_amount_rubles(self, obj):
        return f"{obj.get_amount_rubles()} руб."
    get_amount_rubles.short_description = 'Сумма в рублях'
