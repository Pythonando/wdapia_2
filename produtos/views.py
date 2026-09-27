import json
import logging
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ProdutoForm
from .models import Produto

logger = logging.getLogger('produtos')


@require_http_methods(['GET', 'POST'])
def home(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            try:
                produto = form.save()

                logger.info(
                    json.dumps({
                        'event': 'produto_cadastrado',
                        'produto_id': produto.id,
                        'produto_nome': produto.nome,
                    }),
                    extra={'request_id': getattr(request, 'request_id', None)}
                )
                messages.success(request, 'Produto cadastrado com sucesso.')
                return redirect('produtos:home')
            except Exception as e:
                logger.error(
                    json.dumps({
                        'event': 'produto_save_error',
                        'error': str(e),
                    }),
                    exc_info=True,
                    extra={'request_id': getattr(request, 'request_id', None)}
                )
                messages.error(request, 'Erro ao salvar produto.')
        else:
            logger.warning(
                json.dumps({
                    'event': 'validacao_falhou',
                    'errors': form.errors.as_json(),
                }),
                extra={'request_id': getattr(request, 'request_id', None)}
            )
    else:
        form = ProdutoForm()

    produtos = Produto.objects.all()

    return render(request, 'produtos/home.html', {
        'form': form,
        'produtos': produtos,
    })
