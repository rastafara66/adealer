import logging
import os
from datetime import datetime, timedelta

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log', 'adealer.log')

def log_odoo_error(error_text):
    # Додаємо 3 години до UTC
    now = datetime.utcnow() + timedelta(hours=3)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"{now.strftime('%Y-%m-%d %H:%M:%S')} | {error_text}\n")

def custom_error_middleware(app):
    def middleware(environ, start_response):
        try:
            return app(environ, start_response)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log_odoo_error(tb)
            raise  # Не змінюємо стандартну поведінку Odoo
    return middleware

# Для підключення middleware:
def prestart_hook(server):
    server.wsgi_app = custom_error_middleware(server.wsgi_app)