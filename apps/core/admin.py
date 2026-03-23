from django.contrib import admin
from .models import UploadedFile, CepResult

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'status', 'total_rows', 'created_at' ]
    list_filter = ['status']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CepResult)
class CepResultAdmin(admin.ModelAdmin):
    list_display = ['uploaded_file', 'row_number', 'cep_original', 'cidade', 'bairro', 'found']
    list_filter = ['found']
    

# Register your models here.
