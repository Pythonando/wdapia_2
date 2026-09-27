# Reduzindo complexidade ciclomática: padrões por causa

Cada estrutura de decisão (`if`, `elif`, `for`, `while`, `and`, `or`, `except`,
`with` condicional, comprehension com `if`, expressão ternária, `assert`, `case`)
soma +1 ao CC. Baixar o número é consequência de eliminar a decisão, não de
escondê-la em outra função.

---

## 1. Guard clauses no lugar de aninhamento

O aninhamento não aumenta o CC mais que o `if` plano, mas dispara o crescimento
porque cada nível convida a mais ramos. Inverta e saia cedo.

```python
# Antes — CC cresce e a leitura exige empilhar contexto
def process(submission):
    if submission is not None:
        if submission.status == "pending":
            if submission.user.has_active_plan:
                return run_correction(submission)
            else:
                return deny(submission)
        else:
            return None
    return None

# Depois — mesmo comportamento, cada condição isolada
def process(submission):
    if submission is None:
        return None
    if submission.status != "pending":
        return None
    if not submission.user.has_active_plan:
        return deny(submission)
    return run_correction(submission)
```

---

## 2. Dispatch por dicionário no lugar de `if/elif` longo

Cadeias sobre um valor discreto (tipo de evento, status, provedor) viram tabela.
O CC do dispatcher cai para ~1 e cada handler é testável isoladamente.

```python
# Antes — CC = 6 e cresce a cada novo evento
def handle(event):
    if event.type == "PAYMENT_CONFIRMED":
        ...
    elif event.type == "PAYMENT_OVERDUE":
        ...
    elif event.type == "PAYMENT_REFUNDED":
        ...

# Depois — CC = 2, extensível sem tocar no dispatcher
HANDLERS = {
    "PAYMENT_CONFIRMED": handle_confirmed,
    "PAYMENT_OVERDUE": handle_overdue,
    "PAYMENT_REFUNDED": handle_refunded,
}

def handle(event):
    handler = HANDLERS.get(event.type)
    if handler is None:
        logger.warning("evento não tratado: %s", event.type)
        return
    handler(event)
```

Em Django, o mesmo vale para escolher queryset/serializer/template por parâmetro.

---

## 3. Validações encadeadas → lista de regras

```python
# Antes — cada regra soma +1, a função vira um muro
def validate(essay):
    if not essay.theme:
        raise ValidationError("tema obrigatório")
    if len(essay.body) < 500:
        raise ValidationError("texto curto demais")
    if len(essay.body) > 5000:
        raise ValidationError("texto longo demais")
    ...

# Depois — CC = 3, regras viram dados
RULES = [
    (lambda e: bool(e.theme), "tema obrigatório"),
    (lambda e: len(e.body) >= 500, "texto curto demais"),
    (lambda e: len(e.body) <= 5000, "texto longo demais"),
]

def validate(essay):
    for check, message in RULES:
        if not check(essay):
            raise ValidationError(message)
```

Num projeto Django, prefira ainda um `Form`/`ModelForm` ou validadores de campo —
o framework já faz esse laço.

---

## 4. Condições booleanas compostas → predicado nomeado

`and`/`or` somam ao CC e escondem a intenção.

```python
# Antes — CC +4 numa linha
if user.is_active and user.plan != "NO_PLAN" and not user.is_blocked and user.email_verified:
    ...

# Depois — a condição ganha nome e a view fica com CC +1
# accounts/models.py
@property
def can_access_premium(self) -> bool:
    return (
        self.is_active
        and self.plan != Plan.NO_PLAN
        and not self.is_blocked
        and self.email_verified
    )

if user.can_access_premium:
    ...
```

O CC total não some — migra para onde é coeso e fácil de testar direto.

---

## 5. `try/except` amplo → escopo mínimo

Cada `except` soma +1. Um `try` que envolve 40 linhas com 5 handlers também
mascara qual linha falhou.

```python
# Antes
def correct(submission):
    try:
        payload = build_payload(submission)
        result = agent.run(payload)
        persist(result)
    except APIError:
        ...
    except ValidationError:
        ...
    except Exception:
        ...

# Depois — cada trecho protege só o que pode falhar daquele jeito
def correct(submission):
    payload = build_payload(submission)
    result = _call_agent(payload)      # trata APIError
    _persist(result)                   # trata ValidationError
```

---

## 6. Views Django gordas → camada de serviço

O padrão mais comum de rank D/E neste tipo de projeto: uma view que valida,
consulta, decide, escreve e monta contexto.

```python
# Antes — CC 24 numa única view
def submit_essay(request):
    if request.method == "POST":
        ...  # validação, quota, criação, disparo de task, tratamento de erro

# Depois — view fina, regra em serviço
def submit_essay(request):
    form = EssaySubmissionForm(request.POST)
    if not form.is_valid():
        return render(request, "essay/form.html", {"form": form}, status=400)
    submission = essay_service.submit(request.user, form.cleaned_data)
    return redirect("essay-detail", pk=submission.pk)
```

O serviço concentra a decisão, roda sem `request` e é testável sem cliente HTTP.

---

## 7. Laços com filtro → queryset ou comprehension

```python
# Antes — CC 4, e provável N+1
results = []
for plan in StudyPlan.objects.all():
    if plan.is_public:
        for subject in plan.subjects.all():
            if subject.topics.exists():
                results.append(subject)

# Depois — CC 1, uma query
results = Subject.objects.filter(
    plan__is_public=True, topics__isnull=False
).distinct().select_related("plan")
```

Ganho duplo: menos ramos e menos consultas.

---

## Quando **não** refatorar

- **Migrations do Django** — geradas, nunca editadas à mão.
- **Dispatchers de protocolo externo** já em forma de tabela, onde o `if` restante
  é o fallback.
- **Parsers/máquinas de estado** cuja complexidade é intrínseca ao formato; nesse
  caso, invista em testes de caso-limite em vez de extrair funções.
- **Blocos de configuração declarativa** (`settings.py`, `Meta`, mapeamentos).

Quando um bloco é legitimamente complexo, documente o porquê num comentário curto
e cubra os caminhos com teste. Um rank D justificado e testado é melhor que seis
helpers de uso único espalhados pelo módulo.
