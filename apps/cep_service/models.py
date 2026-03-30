from django.db import models


class CepCache(models.Model):
    cep        = models.CharField(max_length=9, unique=True)
    logradouro = models.CharField(max_length=255, blank=True)
    bairro     = models.CharField(max_length=100, blank=True)
    cidade     = models.CharField(max_length=100, blank=True)
    estado     = models.CharField(max_length=2,   blank=True)
    latitude   = models.CharField(max_length=20,  blank=True)  
    longitude  = models.CharField(max_length=20,  blank=True)  
    found      = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'CEP em cache'
        verbose_name_plural = 'CEPs em cache'

    def __str__(self):
        if self.found:
            return f"{self.cep} — {self.logradouro}, {self.cidade}/{self.estado}"
        return f"{self.cep} — não encontrado"