from django.db import models


class UploadedFile(models.Model):

    # Choices para o campo status
    class Status(models.TextChoices):
        PENDING   = 'pending',    'Aguardando processamento'
        PROCESSING = 'processing', 'Processando'
        DONE      = 'done',       'Concluído'
        ERROR     = 'error',      'Erro'

    original_name   = models.CharField(max_length=255)
    file            = models.FileField(upload_to='uploads/')
    selected_column = models.CharField(max_length=100, blank=True)
    total_rows      = models.IntegerField(default=0)
    status          = models.CharField(
                          max_length=20,
                          choices=Status.choices,
                          default=Status.PENDING
                      )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']  # mais recente primeiro

    def __str__(self):
        return f"{self.original_name} ({self.status})"

class CepResult(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='results'
    )
    row_number    = models.IntegerField()
    cep_original  = models.CharField(max_length=20)
    logradouro    = models.CharField(max_length=255, blank=True)
    bairro        = models.CharField(max_length=100, blank=True)
    cidade        = models.CharField(max_length=100, blank=True)
    estado        = models.CharField(max_length=2,   blank=True)
    latitude      = models.CharField(max_length=20,  blank=True)
    longitude     = models.CharField(max_length=20,  blank=True)
    found         = models.BooleanField(default=False)
    error_message = models.CharField(max_length=255, blank=True)  # ← novo

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        status = "✓" if self.found else "✗"
        return f"Linha {self.row_number} — {self.cep_original} {status}"