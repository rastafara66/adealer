# -*- coding: utf-8 -*-
"""Читання .xlsx через openpyxl (без pandas).

openpyxl входить у стандартні залежності Odoo, тож модуль ставиться чисто
СКРІЗЬ — включно з Odoo Online, де `pip install` недоступний. Раніше тут
використовувався pandas лише заради `read_excel`, що вимагало зовнішньої
залежності й блокувало встановлення в хмарі.
"""
import io
import openpyxl


def read_xlsx_rows(source):
    """Прочитати перший аркуш .xlsx → список словників {заголовок: значення}.

    Мімікрує рядки pandas: у коді далі `row.get('Колонка')`.
    Порожня клітинка → None (безпечно для наявних перевірок `safe_val`).

    source: шлях до файлу (str) АБО bytes / файлоподібний об'єкт.
    """
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
    try:
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        try:
            header = next(it)
        except StopIteration:
            return []
        headers = [str(h).strip() if h is not None else '' for h in header]
        rows = []
        for values in it:
            if values is None or all(v is None for v in values):
                continue
            rows.append({h: v for h, v in zip(headers, values) if h})
        return rows
    finally:
        wb.close()
