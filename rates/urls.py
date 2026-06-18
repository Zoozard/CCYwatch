from django.urls import path
from . import views

app_name = 'rates'

urlpatterns = [
    path('', views.currency_dashboard, name='currency_dashboard'),
    path('analytics/<str:char_code>/', views.currency_analytics, name='currency_analytics'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('watchlist/add/<str:char_code>/', views.add_to_watchlist, name='add_to_watchlist'),
    path('watchlist/remove/<str:char_code>/', views.remove_from_watchlist, name='remove_from_watchlist'),

]
