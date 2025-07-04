# Generated by Django 4.2.7 on 2025-06-15 11:52

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance_kopecks', models.BigIntegerField(default=0, help_text='Баланс в копейках', validators=[django.core.validators.MinValueValidator(0)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='balance', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Баланс пользователя',
                'verbose_name_plural': 'Балансы пользователей',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_kopecks', models.PositiveIntegerField(help_text='Сумма в копейках')),
                ('transaction_type', models.CharField(choices=[('deposit', 'Пополнение'), ('transfer_out', 'Исходящий перевод'), ('transfer_in', 'Входящий перевод')], max_length=20)),
                ('description', models.TextField(blank=True, help_text='Описание операции')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('from_user', models.ForeignKey(blank=True, help_text='Отправитель (null для пополнения)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_transactions', to=settings.AUTH_USER_MODEL)),
                ('to_user', models.ForeignKey(help_text='Получатель', on_delete=django.db.models.deletion.CASCADE, related_name='incoming_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Транзакция',
                'verbose_name_plural': 'Транзакции',
                'ordering': ['-created_at'],
            },
        ),
    ]
