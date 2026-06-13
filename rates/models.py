from django.db import models
from django.contrib.auth.models import User

class Currency(models.Model):
    """Модель для хранения информации о самой валюте"""
    name = models.CharField(max_length=100, verbose_name="Название валюты")
    char_code = models.CharField(max_length=3, unique=True, verbose_name="Буквенный код (USD)")
    num_code = models.CharField(max_length=3, verbose_name="Цифровой код")
    nominal = models.IntegerField(default=1, verbose_name="Номинал")

    def __str__(self):
        return f"{self.char_code} ({self.name})"

    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюты"


class ExchangeRate(models.Model):
    """Модель для хранения истории курсов валют по дням"""
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates', verbose_name="Валюта")
    rate = models.DecimalField(max_length=10, max_digits=10, decimal_places=4, verbose_name="Курс к рублю")
    date_checked = models.DateField(verbose_name="Дата фиксации курса")

    def __str__(self):
        return f"{self.currency.char_code} - {self.rate} на {self.date_checked}"

    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "История курсов"
        # Уникальный индекс, чтобы нельзя было случайно сохранить два курса одной валюты на один день
        unique_together = ('currency', 'date_checked')


class Watchlist(models.Model):
    """Модель для отслеживания целевого курса пользователями"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist', verbose_name="Пользователь")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name="Валюта")
    target_rate = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Целевой курс")
    is_notified = models.BooleanField(default=False, verbose_name="Уведомление отправлено")

    def __str__(self):
        return f"{self.user.username} следит за {self.currency.char_code} (Цель: {self.target_rate})"

    class Meta:
        verbose_name = "Подписка на курс"
        verbose_name_plural = "Подписки на курсы"
