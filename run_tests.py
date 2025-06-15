#!/usr/bin/env python
"""
Скрипт для запуска тестов с измерением покрытия кода
"""
import os
import sys
import subprocess


def run_tests():
    """
    Запускает тесты с измерением покрытия
    """
    print("🧪 Запуск тестов с измерением покрытия...")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'balance_api.settings')
    
    coverage_commands = [
        ['coverage', 'erase'],
        ['coverage', 'run', '--source=.', 'manage.py', 'test'],
        ['coverage', 'report', '--show-missing'],
        ['coverage', 'html']
    ]
    
    for cmd in coverage_commands:
        print(f"Выполняю: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ошибка: {result.stderr}")
            return False
        
        print(result.stdout)
    
    print("✅ Тесты выполнены успешно!")
    print("📊 HTML отчет создан в папке htmlcov/")
    return True


def run_pytest():
    """
    Запускает тесты через pytest
    """
    print("🧪 Запуск тестов через pytest...")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'balance_api.settings')
    
    result = subprocess.run([
        'pytest', 
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--cov-fail-under=95',
        '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'pytest':
        success = run_pytest()
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1) 