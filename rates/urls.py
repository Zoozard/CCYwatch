from django.urls import path
from . import views

app_name = 'rates'

urlpatterns = [
    path('', views.currency_dashboard, name='currency_dashboard'),
    path('analytics/<str:char_code>/', views.currency_analytics, name='currency_analytics'),
]
