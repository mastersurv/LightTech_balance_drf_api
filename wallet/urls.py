from django.urls import path, include
from . import views

urlpatterns = [
    path('balance/', views.get_balance, name='get_balance'),
    path('deposit/', views.deposit_balance, name='deposit_balance'),
    path('transfer/', views.transfer_money, name='transfer_money'),
    path('transactions/', views.get_transactions, name='get_transactions'),
] 