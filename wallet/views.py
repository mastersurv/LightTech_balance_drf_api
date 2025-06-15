from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import UserBalance, Transaction
from .serializers import (
    BalanceSerializer, DepositSerializer, 
    TransferSerializer, TransactionSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balance(request):
    """
    Получение текущего баланса авторизованного пользователя в рублях
    """
    user_balance, created = UserBalance.objects.get_or_create(user=request.user)
    serializer = BalanceSerializer(user_balance)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def deposit_balance(request):
    """
    Пополнение баланса пользователя на указанную сумму в копейках
    
    GET: Показывает форму для пополнения баланса с примером
    POST: Выполняет пополнение баланса
    """
    if request.method == 'GET':
        serializer = DepositSerializer()
        user_balance, created = UserBalance.objects.get_or_create(user=request.user)
        
        return Response({
            'description': 'Пополнение баланса пользователя',
            'current_balance_rubles': float(user_balance.get_balance_rubles()),
            'example': {
                'amount_kopecks': 10000,
                'description': 'Пополнить баланс на 100 рублей (10000 копеек)'
            },
            'form_fields': {
                'amount_kopecks': {
                    'type': 'integer',
                    'required': True,
                    'min_value': 1,
                    'help_text': 'Сумма пополнения в копейках (1 рубль = 100 копеек)',
                    'example_values': [
                        {'value': 100, 'description': '1 рубль'},
                        {'value': 1000, 'description': '10 рублей'},
                        {'value': 10000, 'description': '100 рублей'},
                        {'value': 100000, 'description': '1000 рублей'}
                    ]
                }
            }
        })
    
    serializer = DepositSerializer(data=request.data)
    if serializer.is_valid():
        amount_kopecks = serializer.validated_data['amount_kopecks']
        
        with transaction.atomic():
            user_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=request.user
            )
            user_balance.balance_kopecks += amount_kopecks
            user_balance.save()
            
            Transaction.objects.create(
                to_user=request.user,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                description=f"Пополнение баланса на {amount_kopecks} копеек"
            )
        
        return Response({
            'message': 'Баланс успешно пополнен',
            'deposited_amount_rubles': float(amount_kopecks / 100),
            'deposited_amount_kopecks': amount_kopecks,
            'new_balance_rubles': float(user_balance.get_balance_rubles())
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def transfer_money(request):
    """
    Перевод денег с баланса текущего пользователя на баланс другого пользователя
    
    GET: Показывает форму для перевода денег с примером
    POST: Выполняет перевод денег
    """
    if request.method == 'GET':
        user_balance, created = UserBalance.objects.get_or_create(user=request.user)
        
        sample_users = User.objects.exclude(id=request.user.id)[:3]
        sample_recipients = [
            {'id': user.id, 'username': user.username} 
            for user in sample_users
        ]
        
        return Response({
            'description': 'Перевод денег другому пользователю',
            'current_balance_rubles': float(user_balance.get_balance_rubles()),
            'current_balance_kopecks': user_balance.balance_kopecks,
            'example': {
                'recipient_id': sample_recipients[0]['id'] if sample_recipients else 2,
                'amount_kopecks': 5000,
                'description': 'Перевести 50 рублей (5000 копеек)'
            },
            'sample_recipients': sample_recipients,
            'form_fields': {
                'recipient_id': {
                    'type': 'integer',
                    'required': True,
                    'help_text': 'ID пользователя-получателя',
                },
                'amount_kopecks': {
                    'type': 'integer',
                    'required': True,
                    'min_value': 1,
                    'help_text': 'Сумма перевода в копейках (1 рубль = 100 копеек)',
                    'example_values': [
                        {'value': 500, 'description': '5 рублей'},
                        {'value': 1000, 'description': '10 рублей'},
                        {'value': 5000, 'description': '50 рублей'},
                        {'value': 10000, 'description': '100 рублей'}
                    ]
                }
            }
        })
    
    serializer = TransferSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        recipient_id = serializer.validated_data['recipient_id']
        amount_kopecks = serializer.validated_data['amount_kopecks']
        
        recipient = get_object_or_404(User, id=recipient_id)
        
        with transaction.atomic():
            sender_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=request.user
            )
            
            if sender_balance.balance_kopecks < amount_kopecks:
                return Response({
                    'error': 'Недостаточно средств на балансе'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            recipient_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=recipient
            )
            
            sender_balance.balance_kopecks -= amount_kopecks
            recipient_balance.balance_kopecks += amount_kopecks
            
            sender_balance.save()
            recipient_balance.save()
            
            Transaction.objects.create(
                from_user=request.user,
                to_user=recipient,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.TRANSFER_OUT,
                description=f"Перевод {amount_kopecks} копеек пользователю {recipient.username}"
            )
            
            Transaction.objects.create(
                from_user=request.user,
                to_user=recipient,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.TRANSFER_IN,
                description=f"Получен перевод {amount_kopecks} копеек от пользователя {request.user.username}"
            )
        
        return Response({
            'message': 'Перевод выполнен успешно',
            'recipient_username': recipient.username,
            'amount_rubles': float(amount_kopecks / 100),
            'new_balance_rubles': float(sender_balance.get_balance_rubles())
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    """
    Получение истории транзакций пользователя
    """
    transactions = Transaction.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).order_by('-created_at')
    
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)
