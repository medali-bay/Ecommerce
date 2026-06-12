# Django E-commerce API

A Django REST Framework e-commerce backend with products, categories, orders, stock tracking, dashboard reports, and API documentation.

## Features

- Product and category management
- Product images
- Guest and logged-in customer orders
- Saved customer phone numbers
- Order status actions: validate, cancel, deliver
- Order status history
- Stock movement history
- Manual stock adjustment
- Dashboard statistics
- Revenue and best-selling product reports
- Swagger API documentation

## Tech Stack

- Python
- Django
- Django REST Framework
- SQLite
- drf-spectacular
- django-filter
- django-cors-headers

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
