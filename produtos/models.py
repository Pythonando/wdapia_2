from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Produto(models.Model):
    nome = models.CharField('nome', max_length=100)
    quantidade = models.PositiveIntegerField(
        'quantidade',
        validators=[MinValueValidator(0), MaxValueValidator(1_000_000_000)],
    )
    criado_em = models.DateTimeField('criado em', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criado_em', '-id']
        verbose_name = 'produto'
        verbose_name_plural = 'produtos'

    def __str__(self):
        return f'{self.nome} ({self.quantidade})'
