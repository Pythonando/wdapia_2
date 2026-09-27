from django.test import TestCase
from django.urls import reverse

from .models import Produto


class ProdutoModelTests(TestCase):
    def test_str_mostra_nome_e_quantidade(self):
        produto = Produto(nome='Caneta', quantidade=10)

        self.assertEqual(str(produto), 'Caneta (10)')


class CadastroProdutoTests(TestCase):
    def setUp(self):
        self.url = reverse('produtos:home')

    def post(self, nome, quantidade, **kwargs):
        return self.client.post(self.url, {'nome': nome, 'quantidade': quantidade}, **kwargs)

    def test_cadastro_valido_salva_e_redireciona(self):
        response = self.post('Caneta', '10')

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(Produto.objects.count(), 1)
        produto = Produto.objects.get()
        self.assertEqual(produto.nome, 'Caneta')
        self.assertEqual(produto.quantidade, 10)

    def test_cadastro_valido_mostra_mensagem_e_limpa_formulario(self):
        response = self.post('Caneta', '10', follow=True)

        self.assertContains(response, 'Produto cadastrado com sucesso.')
        self.assertNotContains(response, 'value="Caneta"')

    def test_nome_so_com_espacos_e_rejeitado(self):
        response = self.post('   ', '5')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Produto.objects.count(), 0)
        self.assertIn('nome', response.context['form'].errors)

    def test_nome_tem_espacos_das_pontas_removidos(self):
        self.post('  Lápis  ', '1')

        self.assertEqual(Produto.objects.get().nome, 'Lápis')

    def test_limite_de_tamanho_do_nome(self):
        response = self.post('a' * 101, '1')
        self.assertIn('nome', response.context['form'].errors)
        self.assertEqual(Produto.objects.count(), 0)

        self.post('a' * 100, '1')
        self.assertEqual(Produto.objects.count(), 1)

    def test_quantidades_invalidas_sao_rejeitadas(self):
        for quantidade in ['', '-1', '2.5', 'abc', '1000000001']:
            with self.subTest(quantidade=quantidade):
                response = self.post('Borracha', quantidade)
                self.assertEqual(response.status_code, 200)
                self.assertIn('quantidade', response.context['form'].errors)
        self.assertEqual(Produto.objects.count(), 0)

    def test_limites_validos_de_quantidade(self):
        self.post('Zero', '0')
        self.post('Máximo', '1000000000')

        self.assertEqual(Produto.objects.count(), 2)

    def test_erro_de_validacao_mantem_valores_digitados(self):
        response = self.post('Borracha', '-1')

        self.assertContains(response, 'value="Borracha"')

    def test_nomes_repetidos_sao_permitidos(self):
        self.post('Caneta', '10')
        self.post('Caneta', '10')

        self.assertEqual(Produto.objects.count(), 2)

    def test_metodo_nao_permitido(self):
        response = self.client.put(self.url)

        self.assertEqual(response.status_code, 405)


class ListagemProdutoTests(TestCase):
    def setUp(self):
        self.url = reverse('produtos:home')

    def test_lista_vazia_mostra_mensagem(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhum produto cadastrado ainda.')

    def test_lista_produtos_do_mais_recente_para_o_mais_antigo(self):
        Produto.objects.create(nome='Caneta', quantidade=10)
        Produto.objects.create(nome='Lápis', quantidade=0)

        response = self.client.get(self.url)
        html = response.content.decode()

        self.assertContains(response, 'Caneta')
        self.assertContains(response, '10')
        self.assertContains(response, 'Lápis')
        self.assertNotContains(response, 'Nenhum produto cadastrado ainda.')
        self.assertLess(html.index('Lápis'), html.index('Caneta'))

    def test_empate_no_horario_usa_id_como_desempate(self):
        primeiro = Produto.objects.create(nome='Primeiro', quantidade=1)
        segundo = Produto.objects.create(nome='Segundo', quantidade=2)
        Produto.objects.update(criado_em=primeiro.criado_em)

        html = self.client.get(self.url).content.decode()

        self.assertLess(html.index(segundo.nome), html.index(primeiro.nome))

    def test_produto_recem_cadastrado_aparece_no_topo(self):
        Produto.objects.create(nome='Antigo', quantidade=1)

        response = self.client.post(self.url, {'nome': 'Novo', 'quantidade': '2'}, follow=True)
        html = response.content.decode()

        self.assertLess(html.index('Novo'), html.index('Antigo'))

    def test_lista_aparece_apos_erro_de_validacao(self):
        Produto.objects.create(nome='Existente', quantidade=1)

        response = self.client.post(self.url, {'nome': '', 'quantidade': '1'})

        self.assertContains(response, 'Existente')

    def test_nome_e_exibido_como_texto_literal(self):
        Produto.objects.create(nome='<b>x</b>', quantidade=1)
        Produto.objects.create(nome='Açúcar & Café', quantidade=3)

        response = self.client.get(self.url)

        self.assertContains(response, '&lt;b&gt;x&lt;/b&gt;')
        self.assertNotContains(response, '<b>x</b>')
        self.assertContains(response, 'Açúcar &amp; Café')

    def test_listagem_com_mil_produtos_usa_consultas_constantes(self):
        Produto.objects.bulk_create(
            Produto(nome=f'Produto {i}', quantidade=i) for i in range(1000)
        )

        with self.assertNumQueries(1):
            response = self.client.get(self.url)

        self.assertContains(response, '<li', count=1000)
