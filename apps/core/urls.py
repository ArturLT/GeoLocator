from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.upload_file, name='upload'),
    path('selecionar/', views.select_column, name='select_column'),
    path('processar/<int:pk>/', views.process_file, name='process'),  # ← novo
]