import xml.etree.ElementTree as ET
from datetime import datetime
import time
from datetime import timedelta
import requests
from decimal import Decimal
from .models import Currency, ExchangeRate

def fetch_cbr_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    
    # Добавляем User-Agent, чтобы ЦБ думал, что к нему обращается обычный браузер Chrome
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"API request failed: {e}")
        return False

    try:
        # Получаем сырые байты ответа
        raw_bytes = response.content
        
        # XML-парсеры Python умеют автоматически определять кодировку из заголовка <?xml ... windows-1251"?> 
        # только если им передают чистый байтовый поток (bytes).
        root = ET.fromstring(raw_bytes)
    except Exception as e:
        print(f"XML parsing failed: {e}")
        return False

    # Извлекаем дату из атрибутов корневого тега ValCurs (формат "dd.mm.yyyy")
    date_str = root.attrib.get('Date')
    if date_str:
        current_date = datetime.strptime(date_str, '%d.%m.%Y').date()
    else:
        current_date = datetime.today().date()

    updated_count = 0

    for valute in root.findall('Valute'):
        num_code = valute.find('NumCode').text
        char_code = valute.find('CharCode').text
        nominal = int(valute.find('Nominal').text)
        
        # Безопасно декодируем текстовое название валюты из кодировки ЦБ
        name = valute.find('Name').text
        
        # Меняем запятую на точку для правильной конвертации в число с плавающей точкой
        rate_str = valute.find('Value').text.replace(',', '.')
        rate_value = Decimal(rate_str)

        # 1. Сохраняем или обновляем саму валюту
        currency, created = Currency.objects.update_or_create(
            char_code=char_code,
            defaults={
                'name': name,
                'num_code': num_code,
                'nominal': nominal
            }
        )

        # 2. Сохраняем курс на эту дату в историю
        rate_obj, rate_created = ExchangeRate.objects.get_or_create(
            currency=currency,
            date_checked=current_date,
            defaults={'rate': rate_value}
        )
        
        if rate_created:
            updated_count += 1

    print(f"Success! Added {updated_count} rates for {current_date}")
    return True


def fetch_historical_rates(days_back=30):
    """
    Одним запросом скачивает историю курса доллара и евро за указанный период,
    используя стабильное динамическое API ЦБ РФ.
    """
    url = "https://www.cbr.ru/scripts/XML_dynamic.asp"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Определяем диапазон дат
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)
    
    # Форматируем даты в формат ЦБ: dd/mm/yyyy
    date1 = start_date.strftime('%d/%m/%Y')
    date2 = end_date.strftime('%d/%m/%Y')
    
    # Популярные валюты и их внутренние ID в базе Центробанка
    target_currencies = {
        'USD': 'R01235',
        'EUR': 'R01239',
        'CNY': 'R01375'  # Юань
    }
    
    total_added = 0

    for char_code, cbr_id in target_currencies.items():
        # Берем или создаем саму валюту в БД, если ее еще нет
        currency, _ = Currency.objects.get_or_create(
            char_code=char_code,
            defaults={'name': f'Иностранная валюта {char_code}', 'num_code': '000', 'nominal': 1}
        )
        
        # Формируем параметры запроса динамики
        params = {
            'date_req1': date1,
            'date_req2': date2,
            'VAL_NM_RQ': cbr_id
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
            
            root = ET.fromstring(response.content)
            
            # Пробегаемся по всем записям (тег Record) в ответе
            for record in root.findall('Record'):
                # Читаем дату записи (атрибут Date равен "dd.mm.yyyy")
                rec_date_str = record.attrib.get('Date')
                rec_date = datetime.strptime(rec_date_str, '%d.%m.%Y').date()
                
                # Читаем курс
                rate_str = record.find('Value').text.replace(',', '.')
                rate_value = Decimal(rate_str)
                
                # Читаем номинал (он может меняться, например у юаня)
                nominal = int(record.find('Nominal').text)
                if currency.nominal != nominal:
                    currency.nominal = nominal
                    currency.save()

                # Сохраняем в историю
                _, created = ExchangeRate.objects.get_or_create(
                    currency=currency,
                    date_checked=rec_date,
                    defaults={'rate': rate_value}
                )
                
                if created:
                    total_added += 1
            print(f"Successfully backfilled history for {char_code}")
            
        except Exception as e:
            print(f"Failed to fetch history for {char_code}: {e}")
            continue
            
    print(f"Historical backfill completed. Added {total_added} entries.")
    return True
