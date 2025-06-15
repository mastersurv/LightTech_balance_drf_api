# API для работы с балансом пользователей

Django REST API для управления балансом пользователей и перевода денег между ними.

## Функциональность

- Получение текущего баланса пользователя в рублях
- Пополнение баланса пользователя (в копейках)
- Перевод денег между пользователями
- Ведение полной истории транзакций

## API Endpoints

### Получение баланса
```
GET /api/wallet/balance/
```
Возвращает текущий баланс авторизованного пользователя в рублях.

![image](https://github.com/user-attachments/assets/9c5ba77c-9840-41a4-9c86-056eef2c9553)


### Пополнение баланса
```
POST /api/wallet/deposit/
```
Тело запроса:
```json
{
    "amount_kopecks": 10000
}
```

![image](https://github.com/user-attachments/assets/8c5d8a95-625a-439a-b262-4d547f6e57bf)


### Перевод денег
```
POST /api/wallet/transfer/
```
Тело запроса:
```json
{
    "recipient_id": 2,
    "amount_kopecks": 5000
}
```

![image](https://github.com/user-attachments/assets/45e476ac-258b-4371-9818-ac826202ca06)

Выполненный перевод:
![image](https://github.com/user-attachments/assets/b49cfae3-bacb-40cf-810f-a27e105048ba)


### История транзакций
```
GET /api/wallet/transactions/
```
Возвращает историю всех транзакций пользователя.

![image](https://github.com/user-attachments/assets/370ab183-78bd-488f-9583-df41d0a93aa1)


## Установка и запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта:
```
DB_NAME=balance_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

3. Создайте базу данных PostgreSQL:
```sql
CREATE DATABASE balance_db;
```

4. Выполните миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

6. Запустите сервер:
```bash
python manage.py runserver
```

### Запуск с Docker

Альтернативно, вы можете запустить приложение с помощью Docker:

1. Запустите все сервисы:
```bash
docker-compose up -d
```

2. Выполните миграции в контейнере:
```bash
docker-compose exec web python manage.py migrate
```

3. Создайте суперпользователя в контейнере:
```bash
docker-compose exec web python manage.py createsuperuser
```

4. Приложение будет доступно на `http://localhost:8000`

Для остановки:
```bash
docker-compose down
```

## Аутентификация

API поддерживает session-based аутентификацию через Django REST Framework.

### Веб-интерфейс для входа
```
GET /api/drf-auth/login/
```
Откройте в браузере для входа через веб-форму Django REST Framework.

### Вход через API
```
POST /api/drf-auth/login/
```
Тело запроса (form-data):
```
username=your_username
password=your_password
csrfmiddlewaretoken=<токен из cookies>
```

### Выход
```
POST /api/drf-auth/logout/
```

### Проверка статуса аутентификации
После успешного входа Django автоматически установит session cookies, которые будут использоваться для всех последующих запросов.

### Использование с curl
```bash
# 1. Получить CSRF токен и создать сессию
curl -c cookies.txt http://localhost:8000/api/drf-auth/login/

# 2. Извлечь CSRF токен из cookies
CSRF_TOKEN=$(grep csrftoken cookies.txt | cut -f7)

# 3. Войти в систему
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/drf-auth/login/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d "username=your_username&password=your_password&csrfmiddlewaretoken=$CSRF_TOKEN"

# 4. Использовать API с сессией
curl -b cookies.txt http://localhost:8000/api/wallet/balance/
```

### Использование с Python requests
```python
import requests

session = requests.Session()

# Получить CSRF токен
login_page = session.get('http://localhost:8000/api/drf-auth/login/')
csrf_token = session.cookies['csrftoken']

# Войти в систему
login_data = {
    'username': 'your_username',
    'password': 'your_password',
    'csrfmiddlewaretoken': csrf_token
}
session.post('http://localhost:8000/api/drf-auth/login/', data=login_data)

# Использовать API
response = session.get('http://localhost:8000/api/wallet/balance/')
print(response.json())
```

## Примеры использования

**Важно:** Все примеры требуют предварительной аутентификации через session (см. раздел "Аутентификация").

### Пополнение баланса на 100 рублей (10000 копеек)
```bash
# С использованием сессии
curl -b cookies.txt -X POST http://localhost:8000/api/wallet/deposit/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"amount_kopecks": 10000}'
```

### Перевод 50 рублей (5000 копеек) пользователю с ID=2
```bash
# С использованием сессии
curl -b cookies.txt -X POST http://localhost:8000/api/wallet/transfer/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"recipient_id": 2, "amount_kopecks": 5000}'
```

### Получение текущего баланса
```bash
# С использованием сессии
curl -b cookies.txt http://localhost:8000/api/wallet/balance/
```

### Полный пример с аутентификацией
```bash
# 1. Создать сессию и получить CSRF токен
curl -c cookies.txt http://localhost:8000/api/drf-auth/login/
CSRF_TOKEN=$(grep csrftoken cookies.txt | cut -f7)

# 2. Войти в систему
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/drf-auth/login/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d "username=root&password=your_password&csrfmiddlewaretoken=$CSRF_TOKEN"

# 3. Проверить баланс
curl -b cookies.txt http://localhost:8000/api/wallet/balance/

# 4. Пополнить баланс
curl -b cookies.txt -X POST http://localhost:8000/api/wallet/deposit/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"amount_kopecks": 10000}'
```

## Архитектура

### Модели
- `UserBalance` - хранит баланс каждого пользователя в копейках
- `Transaction` - хранит историю всех операций с балансом

## Тестирование

Проект покрыт комплексными тестами с покрытием близким к 100%.

### Запуск тестов

**Через Makefile (рекомендуется):**
```bash
make test                    # Обычные тесты
make coverage               # Тесты с отчетом покрытия
make html                   # Тесты с HTML отчетом
make full-test              # Полное тестирование с HTML отчетом
```

**Через Docker:**
```bash
docker-compose exec web python manage.py test
docker-compose exec web coverage run --source=. manage.py test
docker-compose exec web coverage report --show-missing
docker-compose exec web coverage html
```

**Через pytest:**
```bash
make pytest
# или
docker-compose exec web pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Структура тестов

- `wallet/test_models.py` - тесты моделей (UserBalance, Transaction)
- `wallet/test_serializers.py` - тесты сериализаторов (API валидация)  
- `wallet/test_views.py` - тесты API endpoints
- `wallet/test_admin.py` - тесты админ-панели
- `wallet/tests.py` - основной модуль тестов

### Покрытие тестами

Текущее покрытие: **88%** (основной код приложения: **100%**)

| Компонент | Покрытие |
|-----------|----------|
| Models | 100% |
| Views | 100% |
| Serializers | 100% |
| Admin | 100% |
| Apps | 100% |

HTML отчет доступен в `htmlcov/index.html` после запуска `make html`.

### Безопасность
- Все операции требуют session-based аутентификации
- CSRF защита для всех POST/PUT/DELETE запросов
- Используются атомарные транзакции базы данных
- Валидация входных данных на уровне сериализаторов
- Блокировка записей при обновлении баланса
- Автоматическое управление сессиями через Django

### Особенности реализации
- Хранение суммы в копейках для избежания проблем с плавающей точкой
- Автоматическое создание баланса при первом обращении
- Ведение подробной истории всех операций
- Проверка достаточности средств перед переводом 
