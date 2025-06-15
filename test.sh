#!/bin/bash

"""
Скрипт автоматизированного тестирования
Может использоваться в CI/CD пайплайнах
"""

set -e

echo "🚀 Запуск автоматизированного тестирования..."

echo "📦 Проверка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не найден"
    exit 1
fi

echo "🔧 Сборка и запуск контейнеров..."
docker-compose up -d --build

echo "⏳ Ожидание готовности сервисов..."
sleep 10

echo "📥 Установка зависимостей..."
docker-compose exec web pip install -q coverage pytest pytest-django pytest-cov

echo "🔄 Выполнение миграций..."
docker-compose exec web python manage.py migrate --verbosity=0

echo "🧪 Запуск тестов с измерением покрытия..."
docker-compose exec web coverage erase
docker-compose exec web coverage run --source=. manage.py test --verbosity=1

echo "📊 Генерация отчетов покрытия..."
docker-compose exec web coverage report --show-missing
docker-compose exec web coverage html

echo "📈 Проверка минимального порога покрытия..."
COVERAGE=$(docker-compose exec web coverage report --format=total)
COVERAGE=${COVERAGE%\%}

if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
    echo "✅ Покрытие тестами: $COVERAGE% (требуется минимум 80%)"
else
    echo "❌ Покрытие тестами: $COVERAGE% (требуется минимум 80%)"
    docker-compose down
    exit 1
fi

echo "🎯 Запуск дополнительных проверок качества кода..."
docker-compose exec web python -m py_compile wallet/*.py || echo "⚠️  Предупреждения компиляции Python"

echo "🏁 Все тесты успешно пройдены!"
echo "📁 HTML отчет доступен в htmlcov/index.html"

if [[ "$1" == "--keep-running" ]]; then
    echo "🔧 Контейнеры оставлены запущенными для разработки"
else
    echo "🛑 Остановка контейнеров..."
    docker-compose down
fi

echo "✨ Тестирование завершено успешно!" 