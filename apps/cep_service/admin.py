from django.contrib import admin
from .models import CepCache

@admin.register(CepCache)
class CepCacheAdmin(admin.ModelAdmin):
    list_display = ['cep', 'logradouro', 'estado', 'cidade', 'bairro', 'found']
    list_filter = ['found', 'estado']
    search_fields = ['cep', 'cidade']

# Register your models here.
