from django.contrib import admin
from .models import Currency, ExchangeRate, Watchlist

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('char_code', 'name', 'num_code', 'nominal')
    search_fields = ('char_code', 'name')

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'rate', 'date_checked')
    list_filter = ('date_checked', 'currency')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'target_rate', 'is_notified')
