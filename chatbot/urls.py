from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.index, name='index'),
    path('reset/', views.reset_chat, name='reset'),  # <-- This line is required
]