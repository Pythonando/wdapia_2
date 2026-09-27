# Feature Specification: Cadastro e Listagem de Produtos na Home

**Feature Branch**: `001-product-registry-home`

**Created**: 2026-09-26

**Status**: Draft

**Input**: User description: "criar uma aplicacao onde na home o usuario cadastra produtos com nome e quantidade e na mesma paginas eles sao listados."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastrar um produto pela home (Priority: P1)

O usuário abre a página inicial, preenche o nome e a quantidade de um produto em um formulário e confirma o cadastro. O produto é salvo e o usuário permanece na mesma página.

**Why this priority**: Cadastrar é a razão de existir da aplicação. Sem isso não há produtos a listar.

**Independent Test**: Abrir a home, preencher "Caneta" com quantidade 10, enviar e confirmar que o produto foi salvo (por exemplo, ao recarregar a página ele continua existindo).

**Acceptance Scenarios**:

1. **Given** o usuário está na home, **When** informa nome "Caneta" e quantidade 10 e confirma, **Then** o produto é salvo, o usuário continua na home e o formulário volta a ficar vazio.
2. **Given** o usuário está na home, **When** tenta confirmar com o nome vazio, **Then** o produto não é salvo e aparece uma mensagem clara indicando que o nome é obrigatório.
3. **Given** o usuário está na home, **When** informa uma quantidade inválida (vazia, negativa, decimal ou texto) e confirma, **Then** o produto não é salvo e aparece uma mensagem clara sobre a quantidade.
4. **Given** um envio falhou por validação, **When** a mensagem de erro é exibida, **Then** os valores digitados continuam preenchidos para que o usuário corrija só o campo com erro.

---

### User Story 2 - Ver os produtos cadastrados na mesma página (Priority: P1)

Na mesma página do formulário, o usuário vê a lista de todos os produtos já cadastrados, com nome e quantidade de cada um.

**Why this priority**: A listagem na mesma tela faz parte do pedido original e é o que confirma ao usuário que o cadastro deu certo.

**Independent Test**: Com produtos já existentes, abrir a home e confirmar que todos aparecem com nome e quantidade corretos.

**Acceptance Scenarios**:

1. **Given** existem produtos cadastrados, **When** o usuário abre a home, **Then** vê todos eles listados com nome e quantidade.
2. **Given** o usuário acabou de cadastrar um produto, **When** o cadastro é concluído, **Then** o novo produto já aparece na lista, no topo.
3. **Given** não existe nenhum produto cadastrado, **When** o usuário abre a home, **Then** vê uma mensagem informando que ainda não há produtos, em vez de uma lista vazia sem explicação.

---

### Edge Cases

- Nome contendo apenas espaços em branco é tratado como vazio e rejeitado. Espaços no início e no fim de um nome válido são removidos antes de salvar.
- Nome com mais de 100 caracteres é rejeitado com mensagem explicando o limite.
- Quantidade zero é aceita, já que um produto pode existir sem nenhuma unidade.
- Quantidade acima de 1.000.000.000 é rejeitada com mensagem explicando o limite.
- Produtos com o mesmo nome podem ser cadastrados mais de uma vez; cada cadastro aparece como um item separado.
- Nomes com acentos, cedilha e caracteres especiais (ex.: "Açúcar & Café") são salvos e exibidos exatamente como digitados, sem ser interpretados como formatação.
- Recarregar a página logo após um cadastro bem-sucedido não cria o mesmo produto de novo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página inicial MUST exibir um formulário com os campos "nome" e "quantidade" e uma ação para confirmar o cadastro.
- **FR-002**: O sistema MUST exigir o nome, com 1 a 100 caracteres depois de remover espaços no início e no fim.
- **FR-003**: O sistema MUST exigir a quantidade, que deve ser um número inteiro entre 0 e 1.000.000.000.
- **FR-004**: O sistema MUST salvar de forma permanente todo produto válido, de modo que ele continue existindo depois que a página for recarregada ou o sistema for reiniciado.
- **FR-005**: Quando algum dado for inválido, o sistema MUST recusar o cadastro, mostrar uma mensagem de erro junto ao campo com problema e manter os valores que o usuário digitou.
- **FR-006**: Depois de um cadastro bem-sucedido, o sistema MUST manter o usuário na home, limpar o formulário e mostrar uma confirmação de que o produto foi cadastrado.
- **FR-007**: A página inicial MUST listar todos os produtos cadastrados com nome e quantidade, do mais recente para o mais antigo.
- **FR-008**: Quando não houver produtos, a página inicial MUST exibir uma mensagem informando que a lista está vazia.
- **FR-009**: Recarregar a página após um cadastro MUST NOT gerar um cadastro duplicado.
- **FR-010**: O sistema MUST exibir o nome dos produtos como texto literal, sem interpretar o conteúdo digitado como formatação ou código.

### Key Entities *(include if feature involves data)*

- **Produto**: um item registrado pelo usuário. Atributos: nome (texto de 1 a 100 caracteres), quantidade (inteiro de 0 a 1.000.000.000) e momento do cadastro (usado para ordenar a lista). Nomes repetidos são permitidos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário que abre a home pela primeira vez consegue cadastrar um produto em menos de 30 segundos, sem instruções.
- **SC-002**: O produto cadastrado aparece na lista da mesma página em até 2 segundos após a confirmação.
- **SC-003**: 100% dos envios com nome vazio ou quantidade inválida são recusados e mostram uma mensagem que identifica o campo com problema.
- **SC-004**: 100% dos produtos cadastrados continuam listados depois de recarregar a página ou reiniciar o sistema.
- **SC-005**: A home continua abrindo em até 2 segundos com 1.000 produtos cadastrados.

## Assumptions

- A aplicação não tem login: qualquer pessoa que acessa a home vê e cadastra na mesma lista compartilhada.
- Editar, excluir, buscar, filtrar e paginar produtos estão fora do escopo desta versão.
- A quantidade representa unidades inteiras; não há unidade de medida nem valores fracionados.
- A interface será em português do Brasil.
- Uso previsto em computador e celular pelo navegador; a página deve ser utilizável nos dois.
- Volume esperado baixo (até alguns milhares de produtos), por isso a lista inteira é exibida sem paginação.
