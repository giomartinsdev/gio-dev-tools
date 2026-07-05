# Tarefa: scaffold de `bzzoiro-acl` e `domain-persister`

Você está trabalhando num monorepo de um pipeline event-driven de dados esportivos.
Vamos adicionar dois serviços novos. Antes de escrever qualquer código, **explore o
repositório e siga as convenções que já existem** — não invente estrutura nova.

## Fase 1 — Descoberta (faça primeiro, não gere código ainda)

1. Liste os serviços existentes e escolha um como referência de layout. Extraia a
   convenção de DDD + CQRS já usada: como estão organizados `domain/`,
   `application/` (command/query handlers), `infrastructure/` e `interfaces/`; onde
   ficam os event handlers/consumers; como o serviço combina FastAPI (surface HTTP)
   com o loop de consumo de mensageria.
2. Leia `infra/persistence.yml` e use **exatamente** o Postgres e o RabbitMQ
   declarados ali (host, porta, credenciais via env, vhost, nomes de rede/volume).
   Não suba um Postgres/Rabbit novo.
3. Leia a documentação do provedor bzzoiro:
   - Hub: https://sports.bzzoiro.com/docs/
   - Football (free): https://sports.bzzoiro.com/docs/football/
   - OpenAPI schema (fonte da verdade dos payloads): https://sports.bzzoiro.com/api/schema/
   - llms.txt: https://sports.bzzoiro.com/.well-known/llms.txt

Ao final da Fase 1, **apresente um plano curto** (estrutura de pastas dos dois
serviços + do módulo de contratos compartilhado + lista de assunções) e só então
implemente. Se algo divergir das convenções do repo, pergunte antes de divergir.

## Stack e restrições (valem para os dois serviços)

- Python **3.14**. FastAPI servido por **gunicorn** com uvicorn workers.
- Os dois serviços são **consumers**; o FastAPI expõe só a superfície HTTP mínima
  (`/health`, `/ready` e o que o padrão do repo já fizer). O loop de consumo roda
  junto, no mesmo padrão dos serviços existentes (lifespan/background task ou
  processo dedicado — siga o que já está lá).
- **DDD + CQRS espelhando os demais projetos**: write side = event store append-only;
  read side = read models materializados. Command/query handlers separados.
- Sem segredos hardcoded: API key do bzzoiro, DSN do Postgres e URL do Rabbit vêm de
  env (Pydantic Settings, no padrão do repo).
- Tudo idempotente e com retry/backoff onde toca rede.

## Contratos de eventos compartilhados

Se já existe um pacote de contratos no repo, **estenda-o**. Se não, crie um pacote
compartilhado (ex.: `packages/events/` ou o local equivalente do repo) com os modelos
Pydantic abaixo. **Invariante central: para eventos de domínio e de análise, a
routing key do RabbitMQ é igual ao `event_type`.** Assim binding e schema nunca
desincronizam.

Envelope:

```python
class EventMeta(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime
    producer: str            # ex.: "acl.bzzoiro", "persister"
    correlation_id: UUID     # a jornada de UMA partida por todo o pipeline
    causation_id: UUID | None = None
```

Eventos de domínio (canônicos, com `event_type: Literal` para virar discriminated
union via `Field(discriminator="event_type")`):

- `match.scheduled` — match_id, competition_id, home_team_id, away_team_id, kickoff_at, venue?
- `match.status_changed` — match_id, status (enum canônico), minute?
- `match.score_updated` — match_id, home_score, away_score, minute
- `match.finished` — match_id, home_score, away_score, statistics
- `odds.snapshot_captured` — match_id, bookmaker, market, selections[{name, price: Decimal}], captured_at

Enum canônico de status: `SCHEDULED | LIVE | FINISHED | POSTPONED | CANCELLED`.

Eventos raw (arquivo) e de análise:

- `raw.feed_received` — source, feed_type, provider_ref (id **do provedor**, fica só
  aqui), payload (json bruto exatamente como chegou)
- `analysis.insight_generated` — insight_id, match_id, market, recommendation,
  confidence, rationale, model, feature_snapshot, generated_at

Versionamento: cada evento carrega `version: Literal[1]`. Novas versões coexistem na
union (`...V2` com `version: Literal[2]`); consumers antigos ignoram, novos fazem
upcast na borda.

## Topologia RabbitMQ (declaração idempotente no startup)

Exchanges `topic`, `durable`. Toda queue com DLX (`dlx.<queue>` → `q.<queue>.dead`).

| Exchange | Routing key | Queue | Binding | Consumidor |
|---|---|---|---|---|
| `ingestion.events` | `raw.{source}.{feed_type}` | `q.archive.raw` | `raw.#` | domain-persister |
| `domain.events` | `= event_type` | `q.persister` | `#` | domain-persister |
| `analysis.events` | `= event_type` | `q.insight.projector` | `analysis.insight_generated` | (fora deste escopo) |

## Serviço 1 — `bzzoiro-acl`

Anti-corruption layer sobre a API de football (free) do bzzoiro. Ninguém a jusante
conhece o formato do bzzoiro.

- Auth: header `Authorization: Token <BZZOIRO_API_KEY>` em toda request.
- Base: `https://sports.bzzoiro.com/football/api/v2/`. Cliente com `httpx` +
  `tenacity`. Paginação `limit`/`offset` (`limit` máx 200), consumindo
  `{count, next, previous, results}` até `next == null`.
- Trate `429` como sinal de rate limit (backoff + respeito a Retry-After); `401/403`
  como erro de config; `404` ignorável por item.
- Agende polls (upcoming/live/finished + odds) com o scheduler que o repo já usa (ou
  APScheduler se não houver). Datas em ISO 8601 UTC; filtro por `YYYY-MM-DD`.
- **Tradução (o coração da ACL):** mapeie o payload do provedor para os eventos de
  domínio canônicos. Exemplos concretos:
  - status `upcoming` → `SCHEDULED`; `live` → `LIVE`; `finished` → `FINISHED`;
    `postponed` → `POSTPONED`; `cancelled` → `CANCELLED`.
  - odds decimais do provedor → `OddsSnapshotCaptured.selections[].price` (Decimal).
- **Resolução de identidade:** o id de partida/time/competição do bzzoiro
  (`provider_ref`) NÃO vaza para o domínio. Mantenha uma tabela de mapping por
  provedor (`provider`, `provider_ref`, `canonical_id`, `entity_type`) e resolva para
  UUIDs canônicos antes de emitir evento de domínio. Primeira vez que vê uma entidade,
  cria o mapping.
- Emissão: publique `raw.feed_received` em `ingestion.events` (routing
  `raw.bzzoiro.{feed_type}`) com o payload cru, **e** os eventos de domínio já
  normalizados em `domain.events`. Propague `correlation_id` (uma partida) e
  `causation_id` desde a borda.

## Serviço 2 — `domain-persister`

Consome o resultado de todos os ACL workers e persiste.

- Consome `q.archive.raw` (todos os `raw.#`) e grava no **event store append-only**
  (tabela JSONB, imutável) — isso habilita reprocessar/reprojetar depois.
- Consome `q.persister` (todos os `domain.events`) e materializa/atualiza os **read
  models** (matches, teams, competitions, odds_snapshots, etc., no padrão CQRS do
  repo). Desserialização por discriminated union (`TypeAdapter(DomainEvent)`), sem
  `if/elif` gigante.
- **Idempotência:** upsert keyed por `event_id` no event store e por chave natural nos
  read models; reentrega de mensagem não pode duplicar nem corromper estado.
- Ack só após commit no Postgres. Mensagem envenenada (schema de provedor novo que
  quebra validação) vai para a DLX sem travar o consumer.

## Definição de pronto

- Plano aprovado na Fase 1 antes da implementação em massa.
- Módulo de contratos compartilhado, importável pelos dois serviços.
- Os dois serviços rodando via gunicorn, declarando topologia de forma idempotente no
  startup, e reusando Postgres/Rabbit de `infra/persistence.yml`.
- Entradas no compose para `bzzoiro-acl` e `domain-persister` (mesma imagem, entrypoints
  distintos, se for o padrão do repo).
- Migrations do event store, da tabela de mapping de identidade e dos read models.
- README curto por serviço: variáveis de env, como rodar, como escalar consumers.
- Testes no padrão do repo: ao menos a tradução da ACL (payload bzzoiro → evento de
  domínio) e a idempotência do persister (reprocessar o mesmo evento não duplica).

Não gere código de produção antes de confirmar as convenções do repo. Ao terminar,
liste o que assumiu e o que ficou pendente.