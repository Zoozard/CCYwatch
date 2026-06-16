from django.shortcuts import render, get_object_or_404
from django.http import Http404
import pandas as pd
from .models import Currency, ExchangeRate

def currency_dashboard(request):
    """Главная страница: список всех валют с их последними курсами"""
    # Получаем самую последнюю дату, за которую у нас есть курсы в БД
    latest_rate = ExchangeRate.objects.order_by('-date_checked').first()
    
    if latest_rate:
        latest_date = latest_rate.date_checked
        # Берем все курсы за эту дату
        rates = ExchangeRate.objects.filter(date_checked=latest_date).select_related('currency')
    else:
        rates = []
        latest_date = None

    context = {
        'rates': rates,
        'latest_date': latest_date
    }
    return render(request, 'rates/dashboard.html', context)


def currency_analytics(request, char_code):
    """Страница аналитики: расчет статистики по валюте с помощью Pandas"""
    currency = get_object_or_404(Currency, char_code=char_code.upper())
    
    # Извлекаем всю историю курсов для этой валюты из БД
    queryset = ExchangeRate.objects.filter(currency=currency).order_by('date_checked')
    
    if not queryset.exists():
        raise Http404("История курсов для данной валюты не найдена")

    # Превращаем queryset Django в DataFrame Pandas для проведения расчетов
    data = list(queryset.values('date_checked', 'rate'))
    df = pd.DataFrame(data)
    
    # Конвертируем типы данных для корректного расчета в Pandas
    df['rate'] = df['rate'].astype(float)
    df['date_checked'] = pd.to_datetime(df['date_checked'])

    # Расчет аналитических показателей с помощью функций Pandas
    stats = {
        'min_rate': df['rate'].min(),
        'max_rate': df['rate'].max(),
        'mean_rate': round(df['rate'].mean(), 4),
        'volatility': round(df['rate'].max() - df['rate'].min(), 4),
    }

    # Подготавливаем списки данных для передачи в JavaScript-график на веб-странице
    chart_labels = df['date_checked'].dt.strftime('%d.%m.%Y').tolist()
    chart_values = df['rate'].tolist()

    context = {
        'currency': currency,
        'stats': stats,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
    }
    return render(request, 'rates/analytics.html', context)
