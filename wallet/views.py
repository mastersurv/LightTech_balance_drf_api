from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
import logging

from .models import UserBalance, Transaction
from .serializers import (
    BalanceSerializer, DepositSerializer, 
    TransferSerializer, TransactionSerializer
)

logger = logging.getLogger('wallet')
transaction_logger = logging.getLogger('wallet.transactions')
security_logger = logging.getLogger('wallet.security')
auth_logger = logging.getLogger('wallet.auth')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balance(request):
    """
    Получение текущего баланса авторизованного пользователя в рублях
    """
    try:
        logger.info(f"Запрос баланса пользователя: {request.user.username} (ID: {request.user.id})")
        
        user_balance, created = UserBalance.objects.get_or_create(user=request.user)
        
        if created:
            logger.info(f"Создан новый баланс для пользователя {request.user.username}: 0.00 руб")
            transaction_logger.info(f"BALANCE_CREATED | user={request.user.username} | balance=0.00")
        
        balance_rubles = float(user_balance.get_balance_rubles())
        logger.debug(f"Текущий баланс пользователя {request.user.username}: {balance_rubles} руб")
        
        serializer = BalanceSerializer(user_balance)
        
        transaction_logger.info(f"BALANCE_VIEW | user={request.user.username} | balance={balance_rubles}")
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса пользователя {request.user.username}: {str(e)}")
        security_logger.error(f"BALANCE_ERROR | user={request.user.username} | error={str(e)}")
        return Response(
            {'error': 'Ошибка при получении баланса'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def deposit_balance(request):
    """
    Пополнение баланса пользователя на указанную сумму в копейках
    
    GET: Показывает форму для пополнения баланса с примером
    POST: Выполняет пополнение баланса
    """
    if request.method == 'GET':
        logger.debug(f"Запрос формы пополнения баланса: {request.user.username}")
        
        try:
            serializer = DepositSerializer()
            user_balance, created = UserBalance.objects.get_or_create(user=request.user)
            
            logger.debug(f"Отправлена форма пополнения для пользователя {request.user.username}")
            
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
        except Exception as e:
            logger.error(f"Ошибка при получении формы пополнения для {request.user.username}: {str(e)}")
            return Response(
                {'error': 'Ошибка при загрузке формы'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    logger.info(f"Начало пополнения баланса пользователя: {request.user.username}")
    logger.debug(f"Данные запроса пополнения: {request.data}")
    
    serializer = DepositSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Ошибка валидации при пополнении баланса пользователя {request.user.username}: {serializer.errors}")
        security_logger.warning(f"DEPOSIT_VALIDATION_ERROR | user={request.user.username} | errors={serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    amount_kopecks = serializer.validated_data['amount_kopecks']
    amount_rubles = float(amount_kopecks / 100)
    
    try:
        with transaction.atomic():
            logger.debug(f"Начало транзакции пополнения для {request.user.username} на {amount_rubles} руб")
            
            user_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=request.user
            )
            
            old_balance = user_balance.balance_kopecks
            old_balance_rubles = float(old_balance / 100)
            
            user_balance.balance_kopecks += amount_kopecks
            user_balance.save()
            
            new_balance_rubles = float(user_balance.get_balance_rubles())
            
            # Создание записи транзакции
            transaction_record = Transaction.objects.create(
                to_user=request.user,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                description=f"Пополнение баланса на {amount_kopecks} копеек"
            )
            
            logger.info(f"Успешное пополнение баланса пользователя {request.user.username}: {amount_rubles} руб")
            transaction_logger.info(
                f"DEPOSIT_SUCCESS | user={request.user.username} | amount={amount_rubles} | "
                f"old_balance={old_balance_rubles} | new_balance={new_balance_rubles} | "
                f"transaction_id={transaction_record.id}"
            )
            
            return Response({
                'message': 'Баланс успешно пополнен',
                'deposited_amount_rubles': amount_rubles,
                'deposited_amount_kopecks': amount_kopecks,
                'new_balance_rubles': new_balance_rubles
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса пользователя {request.user.username}: {str(e)}")
        security_logger.error(
            f"DEPOSIT_ERROR | user={request.user.username} | amount={amount_rubles} | error={str(e)}"
        )
        return Response(
            {'error': 'Ошибка при пополнении баланса'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def transfer_money(request):
    """
    Перевод денег с баланса текущего пользователя на баланс другого пользователя
    
    GET: Показывает форму для перевода денег с примером
    POST: Выполняет перевод денег
    """
    if request.method == 'GET':
        logger.debug(f"Запрос формы перевода денег: {request.user.username}")
        
        try:
            user_balance, created = UserBalance.objects.get_or_create(user=request.user)
            
            sample_users = User.objects.exclude(id=request.user.id)[:3]
            sample_recipients = [
                {'id': user.id, 'username': user.username} 
                for user in sample_users
            ]
            
            logger.debug(f"Отправлена форма перевода для пользователя {request.user.username}")
            
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
        except Exception as e:
            logger.error(f"Ошибка при получении формы перевода для {request.user.username}: {str(e)}")
            return Response(
                {'error': 'Ошибка при загрузке формы'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    logger.info(f"Начало перевода денег от пользователя: {request.user.username}")
    logger.debug(f"Данные запроса перевода: {request.data}")
    
    serializer = TransferSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        logger.warning(f"Ошибка валидации при переводе от пользователя {request.user.username}: {serializer.errors}")
        security_logger.warning(f"TRANSFER_VALIDATION_ERROR | user={request.user.username} | errors={serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    recipient_id = serializer.validated_data['recipient_id']
    amount_kopecks = serializer.validated_data['amount_kopecks']
    amount_rubles = float(amount_kopecks / 100)
    
    try:
        recipient = get_object_or_404(User, id=recipient_id)
        logger.info(f"Попытка перевода {amount_rubles} руб от {request.user.username} к {recipient.username}")
        
        if recipient.id == request.user.id:
            logger.warning(f"Попытка перевода самому себе: {request.user.username}")
            security_logger.warning(f"SELF_TRANSFER_ATTEMPT | user={request.user.username} | amount={amount_rubles}")
            return Response({
                'error': 'Нельзя переводить деньги самому себе'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            logger.debug(f"Начало транзакции перевода от {request.user.username} к {recipient.username}")
            
            sender_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=request.user
            )
            
            if sender_balance.balance_kopecks < amount_kopecks:
                insufficient_amount = float(sender_balance.balance_kopecks / 100)
                logger.warning(
                    f"Недостаточно средств для перевода: {request.user.username} "
                    f"(нужно: {amount_rubles}, есть: {insufficient_amount})"
                )
                security_logger.warning(
                    f"INSUFFICIENT_FUNDS | sender={request.user.username} | recipient={recipient.username} | "
                    f"required={amount_rubles} | available={insufficient_amount}"
                )
                return Response({
                    'error': 'Недостаточно средств на балансе'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            recipient_balance, created = UserBalance.objects.select_for_update().get_or_create(
                user=recipient
            )
            
            sender_old_balance_rubles = float(sender_balance.balance_kopecks / 100)
            recipient_old_balance_rubles = float(recipient_balance.balance_kopecks / 100)
            
            sender_balance.balance_kopecks -= amount_kopecks
            recipient_balance.balance_kopecks += amount_kopecks
            
            sender_balance.save()
            recipient_balance.save()
            
            sender_new_balance_rubles = float(sender_balance.get_balance_rubles())
            recipient_new_balance_rubles = float(recipient_balance.get_balance_rubles())
            
            transfer_out = Transaction.objects.create(
                from_user=request.user,
                to_user=recipient,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.TRANSFER_OUT,
                description=f"Перевод {amount_kopecks} копеек пользователю {recipient.username}"
            )
            
            transfer_in = Transaction.objects.create(
                from_user=request.user,
                to_user=recipient,
                amount_kopecks=amount_kopecks,
                transaction_type=Transaction.TransactionType.TRANSFER_IN,
                description=f"Получен перевод {amount_kopecks} копеек от пользователя {request.user.username}"
            )
            
            logger.info(f"Успешный перевод: {request.user.username} -> {recipient.username} ({amount_rubles} руб)")
            transaction_logger.info(
                f"TRANSFER_SUCCESS | sender={request.user.username} | recipient={recipient.username} | "
                f"amount={amount_rubles} | sender_old_balance={sender_old_balance_rubles} | "
                f"sender_new_balance={sender_new_balance_rubles} | recipient_old_balance={recipient_old_balance_rubles} | "
                f"recipient_new_balance={recipient_new_balance_rubles} | "
                f"out_transaction_id={transfer_out.id} | in_transaction_id={transfer_in.id}"
            )
            
            return Response({
                'message': 'Перевод выполнен успешно',
                'recipient_username': recipient.username,
                'amount_rubles': amount_rubles,
                'new_balance_rubles': sender_new_balance_rubles
            }, status=status.HTTP_200_OK)
            
    except User.DoesNotExist:
        logger.warning(f"Попытка перевода несуществующему пользователю (ID: {recipient_id}) от {request.user.username}")
        security_logger.warning(
            f"TRANSFER_TO_NONEXISTENT_USER | sender={request.user.username} | "
            f"recipient_id={recipient_id} | amount={amount_rubles}"
        )
        return Response({
            'error': 'Пользователь-получатель не найден'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Ошибка при переводе от {request.user.username}: {str(e)}")
        security_logger.error(
            f"TRANSFER_ERROR | sender={request.user.username} | recipient_id={recipient_id} | "
            f"amount={amount_rubles} | error={str(e)}"
        )
        return Response(
            {'error': 'Ошибка при выполнении перевода'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    """
    Получение истории транзакций пользователя
    """
    try:
        logger.info(f"Запрос истории транзакций пользователя: {request.user.username}")
        
        transactions = Transaction.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user)
        ).order_by('-created_at')
        
        transaction_count = transactions.count()
        logger.debug(f"Найдено {transaction_count} транзакций для пользователя {request.user.username}")
        
        serializer = TransactionSerializer(transactions, many=True)
        
        transaction_logger.info(f"TRANSACTIONS_VIEW | user={request.user.username} | count={transaction_count}")
        
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций пользователя {request.user.username}: {str(e)}")
        security_logger.error(f"TRANSACTIONS_ERROR | user={request.user.username} | error={str(e)}")
        return Response(
            {'error': 'Ошибка при получении истории транзакций'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
