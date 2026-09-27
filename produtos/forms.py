from django import forms

from .models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'quantidade']
        widgets = {
            'nome': forms.TextInput(attrs={'maxlength': 100, 'autofocus': True}),
            'quantidade': forms.NumberInput(attrs={'min': 0, 'max': 1000000000, 'step': 1}),
        }
