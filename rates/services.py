import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import requests
from lxml import etree

from .models import Currency, ExchangeRate, Watchlist
from django.contrib import messages

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,text/html;q=0.9",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def fetch_historical_rates(days_back):
    """
    Загружает курсы валют ЦБ РФ за указанное количество дней.

    Для каждой даты автоматически создаёт отсутствующие валюты
    и сохраняет курсы в базе данных.

    Args:
        days_back (int): количество дней истории.

    Returns:
        bool: True, если удалось обработать хотя бы один день.
    """
    today = date.today()
    success_days = 0

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for offset in range(days_back):
            current_date = today - timedelta(days=offset)

            try:
                response = session.get(
                    CBR_URL,
                    params={"date_req": current_date.strftime("%d.%m.%Y")},
                    timeout=15,
                )
                response.raise_for_status()

                xml = etree.fromstring(response.content)

                actual_date = current_date
                xml_date = xml.attrib.get("Date")
                if xml_date:
                    try:
                        actual_date = datetime.strptime(
                            xml_date,
                            "%d.%m.%Y",
                        ).date()
                    except ValueError:
                        pass

                valutes = xml.xpath("//Valute")

                if not valutes:
                    continue

                for valute in valutes:
                    try:
                        currency, _ = Currency.objects.update_or_create(
                            char_code=valute.findtext("CharCode"),
                            defaults={
                                "name": valute.findtext("Name"),
                                "num_code": valute.findtext("NumCode"),
                                "nominal": int(valute.findtext("Nominal")),
                            },
                        )

                        ExchangeRate.objects.get_or_create(
                            currency=currency,
                            date_checked=actual_date,
                            defaults={
                                "rate": Decimal(
                                    valute.findtext("Value").replace(",", ".")
                                )
                            },
                        )

                    except (
                        AttributeError,
                        ValueError,
                        TypeError,
                    ):
                        continue

                success_days += 1
                time.sleep(0.5)

            except (
                requests.RequestException,
                etree.XMLSyntaxError,
            ):
                continue

    return success_days > 0


def ensure_actual_rates():
    """
    Проверяет наличие курсов на текущую дату и запускает алерты.

    Если курсы отсутствуют, автоматически загружает их
    с сайта Центрального банка РФ.
    """
    today = date.today()

    if ExchangeRate.objects.filter(date_checked=today).exists():
        return

    fetch_historical_rates(days_back=1)

def check_watchlist_alerts(request):
    """
    Проверяет активные подписки ТОЛЬКО для текущего авторизованного пользователя
    и выводит ему уведомление на экран через django.contrib.messages.
    """
    if not request.user.is_authenticated:
        return

    # Ищем подписки текущего пользователя, которые еще не выстрелили
    active_alerts = Watchlist.objects.filter(
        user=request.user, 
        is_notified=False
    ).select_related('currency')
    
    latest_rate_obj = ExchangeRate.objects.order_by('-date_checked').first()
    if not latest_rate_obj:
        return
    
    latest_date = latest_rate_obj.date_checked

    for alert in active_alerts:
        current_rate_obj = ExchangeRate.objects.filter(
            currency=alert.currency, 
            date_checked=latest_date
        ).first()
        
        if not current_rate_obj:
            continue
            
        current_rate = current_rate_obj.rate
        target_rate = alert.target_rate

        # Условие: курс стал ниже или равен целевому
        if current_rate <= target_rate:
            messages.success(
                request,
                f"🎯 Сигнал по валюте {alert.currency.char_code} ({alert.currency.name})! "
                f"Курс достиг вашей цели: {current_rate} ₽ (Вы ставили: {target_rate} ₽)."
            )
            
            # Помечаем в БД, что уведомление сработало
            alert.is_notified = True
            alert.save()