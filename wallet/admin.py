from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserBalance, Transaction
import logging


logger = logging.getLogger('wallet')
security_logger = logging.getLogger('wallet.security')


class UserBalanceInline(admin.StackedInline):
    model = UserBalance
    can_delete = False
    verbose_name_plural = 'Баланс'
    readonly_fields = ('created_at', 'updated_at')


class UserAdmin(BaseUserAdmin):
    inlines = (UserBalanceInline,)
    
    def save_model(self, request, obj, form, change):
        """
        Логирование изменений пользователей в админке
        """
        action = "изменен" if change else "создан"
        logger.info(f"Пользователь {obj.username} {action} администратором {request.user.username}")
        security_logger.info(f"ADMIN_USER_ACTION | admin={request.user.username} | target={obj.username} | action={action}")
        super().save_model(request, obj, form, change)


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_kopecks', 'get_balance_rubles', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_balance_rubles(self, obj):
        return f"{obj.get_balance_rubles()} ₽"
    get_balance_rubles.short_description = 'Баланс в рублях'
    
    def save_model(self, request, obj, form, change):
        """
        Логирование изменений баланса в админке
        """
        action = "изменен" if change else "создан"
        old_balance = None
        
        if change and 'balance_kopecks' in form.changed_data:
            try:
                old_instance = UserBalance.objects.get(pk=obj.pk)
                old_balance = old_instance.balance_kopecks
            except UserBalance.DoesNotExist:
                old_balance = 0
        
        super().save_model(request, obj, form, change)
        
        if old_balance is not None and old_balance != obj.balance_kopecks:
            old_balance_rubles = float(old_balance / 100)
            new_balance_rubles = float(obj.get_balance_rubles())
            logger.warning(
                f"Баланс пользователя {obj.user.username} изменен администратором {request.user.username}: "
                f"{old_balance_rubles} -> {new_balance_rubles} руб"
            )
            security_logger.warning(
                f"ADMIN_BALANCE_CHANGE | admin={request.user.username} | user={obj.user.username} | "
                f"old_balance={old_balance_rubles} | new_balance={new_balance_rubles}"
            )
        else:
            logger.info(f"Баланс пользователя {obj.user.username} {action} администратором {request.user.username}")
            security_logger.info(
                f"ADMIN_BALANCE_ACTION | admin={request.user.username} | user={obj.user.username} | action={action}"
            )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_from_user', 'to_user', 'amount_kopecks', 'get_amount_rubles', 'transaction_type', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('from_user__username', 'to_user__username', 'description')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    
    def get_from_user(self, obj):
        return obj.from_user.username if obj.from_user else "Система"
    get_from_user.short_description = 'Отправитель'
    
    def get_amount_rubles(self, obj):
        return f"{obj.get_amount_rubles()} ₽"
    get_amount_rubles.short_description = 'Сумма в рублях'
    
    def save_model(self, request, obj, form, change):
        """
        Логирование изменений транзакций в админке
        """
        action = "изменена" if change else "создана"
        
        super().save_model(request, obj, form, change)
        
        from_user_name = obj.from_user.username if obj.from_user else "Система"
        logger.warning(
            f"Транзакция {action} администратором {request.user.username}: "
            f"{from_user_name} -> {obj.to_user.username} ({obj.get_amount_rubles()} руб) [ID: {obj.id}]"
        )
        security_logger.warning(
            f"ADMIN_TRANSACTION_ACTION | admin={request.user.username} | "
            f"from_user={from_user_name} | to_user={obj.to_user.username} | "
            f"amount={float(obj.get_amount_rubles())} | transaction_id={obj.id} | action={action}"
        )
    
    def delete_model(self, request, obj):
        """
        Логирование удаления транзакций в админке
        """
        from_user_name = obj.from_user.username if obj.from_user else "Система"
        logger.error(
            f"Транзакция удалена администратором {request.user.username}: "
            f"{from_user_name} -> {obj.to_user.username} ({obj.get_amount_rubles()} руб) [ID: {obj.id}]"
        )
        security_logger.error(
            f"ADMIN_TRANSACTION_DELETE | admin={request.user.username} | "
            f"from_user={from_user_name} | to_user={obj.to_user.username} | "
            f"amount={float(obj.get_amount_rubles())} | transaction_id={obj.id}"
        )
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """
        Логирование массового удаления транзакций в админке
        """
        transaction_count = queryset.count()
        logger.error(
            f"Массовое удаление {transaction_count} транзакций администратором {request.user.username}"
        )
        security_logger.error(
            f"ADMIN_BULK_TRANSACTION_DELETE | admin={request.user.username} | count={transaction_count}"
        )
        super().delete_queryset(request, queryset)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
