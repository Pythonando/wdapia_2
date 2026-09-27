# Observabilidade (Elastic Stack)

## Subir
```bash
cd observability
cp .env.example .env            # troque senhas e chaves
sudo sysctl -w vm.max_map_count=262144
docker compose up -d --build    # a 1a subida leva alguns minutos (dashboards dos beats)
```
Django (na raiz do projeto), **escutando em todas as interfaces** para o Heartbeat alcançar:
```bash
cp .env.example .env
python manage.py runserver 0.0.0.0:8000
```

## Acesso
Kibana: http://localhost:5601 — usuário `elastic`, senha = `ELASTIC_PASSWORD` do `observability/.env`.

## Variáveis (Django, `.env` na raiz)
`ELASTIC_APM_SERVER_URL`, `ELASTIC_APM_SERVICE_NAME`, `ELASTIC_APM_ENVIRONMENT`, `ELASTIC_APM_SECRET_TOKEN`,
`ELASTIC_APM_TRANSACTION_SAMPLE_RATE`, `ELASTIC_APM_DISABLE_SEND`, `LOG_DIR`, `LOG_LEVEL`, `SLOW_REQUEST_MS`, `ALLOWED_HOSTS`.
`LOG_DIR` deve apontar para a mesma pasta de `APP_LOG_DIR` da stack (padrão `observability/app-logs`).

## Onde ver cada dado
| Dado | Kibana |
|---|---|
| Fluxo de requisição, tempo de resposta, spans SQL/template | Observability → APM → Services → `teste-wdapia` → Transactions |
| Erros | APM → Errors (e logs com tag `app-error`) |
| Logs (com correlação ao trace) | Observability → Logs / Discover (`filebeat-*`); na transação do APM, aba *Logs* |
| CPU/RAM/disco/rede (host e containers) | Observability → Infrastructure, dashboards `[Metricbeat System]` |
| Disponibilidade e RTT | Observability → Uptime / Synthetics (`heartbeat-*`) |

## Troubleshooting
- **Heartbeat mostra o Django "down" (connection refused):** o Django está em `127.0.0.1`. Use `runserver 0.0.0.0:8000`.
- **Django responde 400 ao Heartbeat:** falta `host.docker.internal` em `ALLOWED_HOSTS`.
- **Sem logs no Kibana:** confira permissão de `observability/app-logs` (deve ser do seu usuário; se o Docker criou como root: `docker run --rm -v "$PWD/app-logs:/d" alpine chown $(id -u):$(id -g) /d`).
- **Sem traces:** `curl localhost:8200` deve responder e o serviço `setup-apm` precisa ter terminado com sucesso (`docker compose ps -a`).
- **Elasticsearch não sobe:** `vm.max_map_count` baixo ou pouca RAM (ajuste `ES_JAVA_OPTS`).
- Se o APM Server estiver fora do ar, o Django continua funcionando normalmente.
