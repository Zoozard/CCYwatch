import xml.etree.ElementTree as ET
from datetime import datetime
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
