.PHONY: test coverage report html install build up down clean

test:
	docker-compose exec web python manage.py test

coverage:
	docker-compose exec web coverage erase
	docker-compose exec web coverage run --source=. manage.py test
	docker-compose exec web coverage report --show-missing

html:
	docker-compose exec web coverage erase
	docker-compose exec web coverage run --source=. manage.py test
	docker-compose exec web coverage html
	@echo "HTML отчет создан в htmlcov/index.html"

install:
	docker-compose exec web pip install -r requirements.txt

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	docker-compose down -v
	docker system prune -f

pytest:
	docker-compose exec web pytest --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=95 -v

full-test: up coverage html
	@echo "✅ Полное тестирование завершено с HTML отчетом" 