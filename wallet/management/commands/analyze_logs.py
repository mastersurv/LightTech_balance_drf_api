import os
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Анализ логов безопасности и транзакций'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Количество дней для анализа (по умолчанию: 7)'
        )
        parser.add_argument(
            '--type',
            choices=['security', 'transactions', 'all'],
            default='all',
            help='Тип анализа логов'
        )

    def handle(self, *args, **options):
        days = options['days']
        analysis_type = options['type']
        
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        
        if not os.path.exists(logs_dir):
            self.stdout.write(
                self.style.ERROR('Директория логов не найдена. Убедитесь, что логирование настроено.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Анализ логов за последние {days} дней...\n')
        )

        if analysis_type in ['security', 'all']:
            self.analyze_security_logs(logs_dir, days)
            
        if analysis_type in ['transactions', 'all']:
            self.analyze_transaction_logs(logs_dir, days)

    def analyze_security_logs(self, logs_dir, days):
        """Анализ логов безопасности"""
        security_log_path = os.path.join(logs_dir, 'security.log')
        
        if not os.path.exists(security_log_path):
            self.stdout.write(
                self.style.WARNING('Файл security.log не найден')
            )
            return

        self.stdout.write(self.style.SUCCESS('=== АНАЛИЗ БЕЗОПАСНОСТИ ==='))
        
        login_attempts = defaultdict(int)
        failed_logins = defaultdict(int)
        suspicious_activities = []
        rate_limit_violations = []
        admin_actions = []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with open(security_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    date_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if date_match:
                        log_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_date < cutoff_date:
                            continue
                    
                    if 'LOGIN_SUCCESS' in line:
                        user_match = re.search(r'user=(\w+)', line)
                        if user_match:
                            login_attempts[user_match.group(1)] += 1
                    
                    elif 'LOGIN_FAILED' in line:
                        user_match = re.search(r'username=(\w+)', line)
                        if user_match:
                            failed_logins[user_match.group(1)] += 1
                    
                    elif 'RATE_LIMIT_EXCEEDED' in line:
                        rate_limit_violations.append(line.strip())
                    
                    elif 'ADMIN_' in line:
                        admin_actions.append(line.strip())
                    
                    elif any(suspicious in line for suspicious in [
                        'LARGE_DEPOSIT_ATTEMPT', 'LARGE_TRANSFER_ATTEMPT',
                        'SELF_TRANSFER_ATTEMPT', 'INSUFFICIENT_FUNDS'
                    ]):
                        suspicious_activities.append(line.strip())

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при чтении security.log: {str(e)}')
            )
            return

        self.stdout.write(f'\n📊 Статистика входов в систему:')
        for user, count in sorted(login_attempts.items(), key=lambda x: x[1], reverse=True)[:10]:
            self.stdout.write(f'  {user}: {count} успешных входов')

        if failed_logins:
            self.stdout.write(f'\n⚠️  Неудачные попытки входа:')
            for user, count in sorted(failed_logins.items(), key=lambda x: x[1], reverse=True)[:10]:
                self.stdout.write(f'  {user}: {count} неудачных попыток')

        if suspicious_activities:
            self.stdout.write(f'\n🚨 Подозрительная активность ({len(suspicious_activities)} событий):')
            for activity in suspicious_activities[-5:]:
                self.stdout.write(f'  {activity}')

        if rate_limit_violations:
            self.stdout.write(f'\n⚡ Превышения лимита запросов ({len(rate_limit_violations)} событий):')
            for violation in rate_limit_violations[-3:]:
                self.stdout.write(f'  {violation}')

        if admin_actions:
            self.stdout.write(f'\n👤 Действия администраторов ({len(admin_actions)} событий):')
            for action in admin_actions[-5:]:
                self.stdout.write(f'  {action}')

    def analyze_transaction_logs(self, logs_dir, days):
        """Анализ логов транзакций"""
        transaction_log_path = os.path.join(logs_dir, 'transactions.log')
        
        if not os.path.exists(transaction_log_path):
            self.stdout.write(
                self.style.WARNING('Файл transactions.log не найден')
            )
            return

        self.stdout.write(self.style.SUCCESS('\n=== АНАЛИЗ ТРАНЗАКЦИЙ ==='))
        
        user_deposits = defaultdict(float)
        user_transfers_out = defaultdict(float)
        user_transfers_in = defaultdict(float)
        total_volume = 0.0
        transaction_count = 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with open(transaction_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    date_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if date_match:
                        log_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_date < cutoff_date:
                            continue
                    
                    if 'DEPOSIT_SUCCESS' in line:
                        user_match = re.search(r'user=(\w+)', line)
                        amount_match = re.search(r'amount=([0-9.]+)', line)
                        if user_match and amount_match:
                            user = user_match.group(1)
                            amount = float(amount_match.group(1))
                            user_deposits[user] += amount
                            total_volume += amount
                            transaction_count += 1
                    
                    elif 'TRANSFER_SUCCESS' in line:
                        sender_match = re.search(r'sender=(\w+)', line)
                        recipient_match = re.search(r'recipient=(\w+)', line)
                        amount_match = re.search(r'amount=([0-9.]+)', line)
                        
                        if sender_match and recipient_match and amount_match:
                            sender = sender_match.group(1)
                            recipient = recipient_match.group(1)
                            amount = float(amount_match.group(1))
                            
                            user_transfers_out[sender] += amount
                            user_transfers_in[recipient] += amount
                            total_volume += amount
                            transaction_count += 1

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при чтении transactions.log: {str(e)}')
            )
            return

        self.stdout.write(f'\n📈 Общая статистика:')
        self.stdout.write(f'  Всего транзакций: {transaction_count}')
        self.stdout.write(f'  Общий объем: {total_volume:.2f} ₽')
        if transaction_count > 0:
            self.stdout.write(f'  Средняя сумма: {total_volume/transaction_count:.2f} ₽')

        if user_deposits:
            self.stdout.write(f'\n💰 Топ пополнений:')
            for user, amount in sorted(user_deposits.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.stdout.write(f'  {user}: {amount:.2f} ₽')

        if user_transfers_out:
            self.stdout.write(f'\n📤 Топ отправителей:')
            for user, amount in sorted(user_transfers_out.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.stdout.write(f'  {user}: {amount:.2f} ₽ отправлено')

        if user_transfers_in:
            self.stdout.write(f'\n📥 Топ получателей:')
            for user, amount in sorted(user_transfers_in.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.stdout.write(f'  {user}: {amount:.2f} ₽ получено')

        self.stdout.write('\n✅ Анализ завершен') 