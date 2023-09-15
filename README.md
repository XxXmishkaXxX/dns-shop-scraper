# Скрапер DNS Shop

Этот скрипт на Python предназначен для сбора информации о продуктах с веб-сайта DNS Shop. Он извлекает такие данные, как модель, цена, описание, характеристики и изображения для различных категорий компьютерных компонентов.

## Требования
- Python 3.x
- Необходимые библиотеки: `asyncio`, `datetime`, `multiprocessing`, `os`, `queue`, `threading`, `time`, `json`, `pandas`, `aiohttp`, `beautifulsoup4`, `prettytable`, `selenium`, `selenium_stealth`

```bash
pip install asyncio datetime multiprocessing os queue threading time json pandas aiohttp beautifulsoup4 prettytable selenium selenium-stealth
```

## Использование

1. Клонировать репозиторий:
   ```bash
   git clone https://github.com/XxXmishkaXxX/dns-shop-scraper.git
   ```

2. Перейти в каталог проекта:
   ```bash
   cd dns-shop-scraper
   ```

3. Запустить скрипт:
   ```bash
   python new_scraper.py
   ```

4. Следовать инструкциям на экране для выбора категорий для парсинга.

5. Данные будут сохранены в Excel-файлах в соответствующих папках категорий.

## Вклад в разработку
Pull-запросы приветствуются. Для существенных изменений предварительно создайте задачу, чтобы обсудить, что вы хотите изменить.

