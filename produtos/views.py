from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ProdutoForm
from .models import Produto


@require_http_methods(['GET', 'POST'])
def home(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso.')
            return redirect('produtos:home')
    else:
        form = ProdutoForm()

    return render(request, 'produtos/home.html', {
        'form': form,
        'produtos': Produto.objects.all(),
    })
