from django.urls import path
from . import web_views

app_name = 'auth'

urlpatterns = [
    path('login/', web_views.web_login, name='login'),
    path('logout/', web_views.web_logout, name='logout'),
    path('profile/', web_views.web_profile, name='profile'),
]