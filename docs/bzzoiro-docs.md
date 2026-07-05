# Bzzoiro Sports Data (BSD) — Referência compilada

> Compilado de https://sports.bzzoiro.com/docs/ em 2026-07-05.
> Cobre: convenções comuns, endpoints REST de football e a API WebSocket (football).
> Não incluído: params completos por endpoint REST (a página `/docs/football/` é
> renderizada via JS e o `openapi.json`/`.yaml` retornou 500 no momento da captura).
> Fontes definitivas de schema: Swagger `/api/docs/`, ReDoc `/api/redoc/`,
> OpenAPI `/api/schema/`.

---

## 1. Autenticação (igual para todo sport)

Toda request precisa da API key no header `Authorization`. Registre em
`https://sports.bzzoiro.com/register/` → conta → copie a API key.

```
Authorization: Token YOUR_API_KEY
```

curl:
```bash
curl -H "Authorization: Token YOUR_API_KEY" \
  "https://sports.bzzoiro.com/tennis/api/v2/matches/live/"
```

Python:
```python
import requests
headers = {"Authorization": "Token YOUR_API_KEY"}
r = requests.get("https://sports.bzzoiro.com/tennis/api/v2/matches/live/", headers=headers)
print(r.json())
```

Mesma token vale para REST e WebSocket.

---

## 2. Sports e preços

| Sport | Acesso |
|---|---|
| Football | **Free** — match data, live scores, standings, ML predictions, xG shotmaps, odds, 30+ ligas |
| Tennis | Pro $5/mo |
| CS2 / Esports | Pro $5/mo |
| Darts | Pro $5/mo |
| Hockey | Pro $5/mo |
| Live WebSocket (football + tennis) | Addon **$3/mo** |
| MCP (agentes de IA) | Pro $5/mo |
| Odds API (12+ sports, per-bookmaker) | Addon **$5/mo** |

> Football é o único free. **Odds detalhada por bookmaker é addon pago**, e o
> WebSocket também. O REST de football já traz odds agregada (1X2, O/U, BTTS).

---

## 3. Convenções comuns (valem para todo sport)

### Paginação
Todo endpoint de lista é paginado. `limit` (page size, default 50, máx 200) e
`offset` (quantos itens pular, default 0).

```
GET /tennis/api/v2/matches/?limit=50&offset=0    # itens 1–50
GET /tennis/api/v2/matches/?limit=50&offset=50   # itens 51–100
```

Formato da resposta:
```json
{
  "count": 408,
  "next": "https://...",   // URL da próxima página (null na última)
  "previous": null,
  "results": [ ]
}
```
Pagine até `next == null`.

### Datas e horas
ISO 8601, UTC. Ex.: `2026-06-06T14:00:00+00:00`. Ao filtrar por data, passe `YYYY-MM-DD`.

### Match status
Cinco valores canônicos do provedor (a doc chama de "three primary" mas lista cinco):

| Status | Significado |
|---|---|
| `upcoming` | Ainda não começou |
| `live` | Em andamento |
| `finished` | Terminou, resultado final |
| `cancelled` | Cancelado antes de começar |
| `postponed` | Remarcado para data futura |

### Odds
Formato decimal (ex.: `1.85`). `null` = mercado indisponível.

### HTTP status codes
| Código | Significado |
|---|---|
| `200` | Sucesso |
| `401` | Token ausente ou inválido |
| `403` | Conta sem acesso ao sport (Pro required) |
| `404` | Item inexistente |
| `429` | Rate limit excedido |

> Nota: o `llms.txt` afirma "Rate limits: None" para football, enquanto o hub
> documenta `429`. Trate `429` defensivamente mesmo assim (backoff + Retry-After).

---

## 4. Football — endpoints REST

Base (football, via `llms.txt`): `https://sports.bzzoiro.com/api/`
Formato: JSON. Auth: `Authorization: Token YOUR_API_KEY`.

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/leagues/` | Ligas de football ativas |
| GET | `/api/teams/?country=` | Times (filtrável por país) |
| GET | `/api/events/?date_from=&date_to=&league=&status=&tz=` | Partidas com odds |
| GET | `/api/live/?tz=` | Live scores em tempo real com incidentes e estatísticas |
| GET | `/api/predictions/?upcoming=true&tz=` | Predições ML (CatBoost) |
| GET | `/api/players/?team=&nationality=&position=` | Perfis de jogadores (8900+) |
| GET | `/api/player-stats/?player=&event=&team=` | Stats por partida (139k+) |
| GET | `/img/{type}/{id}/` | Logos de times/ligas e fotos de jogadores |

> **Ambiguidade de versão a resolver:** o `llms.txt` usa `/api/events/`,
> `/api/live/`, etc. (sem versão), enquanto a doc do WebSocket referencia
> `/api/v2/events/live/` para descobrir event IDs live, e o exemplo de tennis usa
> `/tennis/api/v2/...`. Confirme a base e o prefixo de versão definitivos no Swagger
> (`/api/docs/`) antes de fixar o cliente REST. O provável é: football na raiz
> (`/api/...`) e demais sports namespaced (`/{sport}/api/v2/...`).

### Cobertura de dados (football)
- 30+ ligas (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, etc.)
- Live scores minuto a minuto com incidentes
- Odds: 1X2, Over/Under 1.5/2.5/3.5, BTTS
- Predições CatBoost com score de confiança
- 8.900+ jogadores com market value
- 139.000+ stats por partida (goals, assists, xG, xA, passes, tackles, etc.)
- Logos e fotos
- Sem dados históricos antes de 2010; sem predições de ligas femininas

---

## 5. WebSocket — football (Addon $3/mo)

### Conexão
```
wss://sports.bzzoiro.com/live/football/?token=YOUR_TOKEN
```
Mesma token do REST. Uma subscription cobre football e tennis. Basic tick ~5s;
Full push por ação em ~100ms.

Latências / limites:
- Ball / score frames: ~5s (Basic) ou por-ação (Full)
- Odds + snapshot da partida: ~30s
- 10 partidas concorrentes por socket (mistura football+tennis)
- 30 frames replayed no subscribe (estado mais recente)
- Server não manda ping espontâneo; envie `{"action":"ping"}` se o socket ficar
  ocioso >60s (responde `{"type":"pong"}`)

### Subscribe / Unsubscribe (outbound)
```json
{ "action": "subscribe",   "event_id": 204849 }
{ "action": "unsubscribe", "event_id": 204849 }
{ "action": "ping" }
```
Ache event IDs live em `/api/v2/events/live/`. No subscribe você recebe imediatamente
um frame `subscribed` com `event`, `livedata` e `odds` atuais.

### Basic vs Full
O frame `subscribed` traz `source`:
- **Basic** (`"basic"`, ~5s): ball x/y, score/minute/period, odds ~30s, xG/shots/possession. Sem `action`.
- **Full** (`"full"`, ~100ms): tudo do Basic + frames `action` por evento em campo, com x/y, atribuição de player/team e `qualifiers`. Só em jogos top-tier (PL, La Liga, UCL...); os demais caem para Basic.

### Frames inbound

**subscribed** — estado completo logo após subscribe:
```json
{
  "type": "subscribed",
  "event_id": 204849,
  "source": "basic",
  "event": {  },
  "livedata": [  ],
  "history": [],
  "odds": {  }
}
```

**event** — snapshot da partida (a cada ~30s e em qualquer mudança de status/score):
```json
{
  "type": "event",
  "event_id": 204849,
  "home": { "id": 17, "name": "Arsenal" },
  "away": { "id": 32, "name": "Chelsea" },
  "score": { "home": 1, "away": 1 },
  "minute": 67,
  "period": "2H",
  "status": { "name": "live" },
  "stats": {
    "home": { "shots": 8, "shots_on_target": 3, "xg": 1.24, "possession": 54 },
    "away": { "...": "same shape" }
  }
}
```
`period`: `1H | 2H | ET1 | ET2 | P`.

**livedata** — posição da bola. Basic ~5s; Full por ação. x/y são % do campo (0–100 esq→dir, 0–100 baixo→cima):
```json
{
  "type": "livedata",
  "event_id": 204849,
  "uts": 1718780400123,
  "x": 62.4,
  "y": 48.7,
  "situation": "corner_kick",
  "minute": 67,
  "period": "2H"
}
```
`situation`: `free_kick | corner_kick | goal_kick | throw_in | penalty | kick_off | regular_play`.

**action** (Full only) — evento por ação com x/y, dentro de ~100ms:
```json
{
  "type": "action",
  "event_id": 204849,
  "action_type": "shot",
  "tid": 4419281,
  "x": 87.3, "y": 51.2,
  "team": "home",
  "player": { "id": 11843, "name": "Saka" },
  "score": { "home": 1, "away": 1 },
  "qualifiers": ["on_target", "right_foot"],
  "minute": 67, "second": 34,
  "period": "2H",
  "ts": 1718780434000
}
```
`action_type`: `shot | pass | tackle | foul | yellow_card | red_card | goal | save | clearance | interception | corner | substitution | offside | var_review`.

**odds** — melhores odds agregadas entre bookmakers (~30s e em movimento de linha relevante):
```json
{
  "type": "odds",
  "event_id": 204849,
  "uts": 1718780400000,
  "odds": {
    "1x2":     { "home": 2.10, "draw": 3.40, "away": 3.60 },
    "over_15": { "over": 1.18, "under": 4.80 },
    "over_25": { "over": 1.90, "under": 1.90 },
    "over_35": { "over": 3.20, "under": 1.33 },
    "btts":    { "yes":  1.72, "no":   2.05 }
  }
}
```

**odds_book** — odds por bookmaker (junto do `odds`), filtre por `bookmaker_slug`:
```json
{
  "type": "odds_book",
  "event_id": 204849,
  "bookmaker_slug": "bet365",
  "uts": 1718780400000,
  "odds": { "1x2": { "home": 2.10, "draw": 3.40, "away": 3.60 } }
}
```

### Error codes (WebSocket)
| code | Descrição |
|---|---|
| `auth_failed` | Token ausente, inválido ou expirado |
| `subscription_required` | Token válido mas addon WS inativo |
| `not_tracked` | Partida existe mas sem tracking live agora |
| `limit` | Limite de 10 partidas concorrentes atingido |
| `bad_action` | Valor de `action` desconhecido |
| `bad_event_id` | `event_id` não encontrado |

Frame de erro:
```json
{ "type": "error", "code": "not_tracked", "message": "No live tracking for event 204849", "event_id": 204849 }
```

### Exemplo Python (asyncio)
```python
import asyncio, json, websockets

TOKEN = "YOUR_TOKEN"
URL = f"wss://sports.bzzoiro.com/live/football/?token={TOKEN}"

async def main():
    async with websockets.connect(URL) as ws:
        await ws.send(json.dumps({"action": "subscribe", "event_id": 204849}))
        async for message in ws:
            frame = json.loads(message)
            if frame["type"] == "livedata":
                print(f'Ball at ({frame["x"]:.1f}, {frame["y"]:.1f}) — {frame["situation"]}')
            elif frame["type"] == "event":
                s = frame["score"]
                print(f'{frame["home"]["name"]} {s["home"]}–{s["away"]} {frame["away"]["name"]} [{frame["minute"]}\']')

asyncio.run(main())
```

---

## 6. Recursos de desenvolvedor

| Recurso | URL |
|---|---|
| API Hub | https://sports.bzzoiro.com/docs/ |
| Football docs | https://sports.bzzoiro.com/docs/football/ |
| WebSocket docs | https://sports.bzzoiro.com/docs/websocket/ |
| WebSocket football | https://sports.bzzoiro.com/docs/websocket/football/ |
| MCP reference | https://sports.bzzoiro.com/docs/mcp/ |
| Odds API | https://sports.bzzoiro.com/odds/ |
| Swagger UI | https://sports.bzzoiro.com/api/docs/ |
| ReDoc | https://sports.bzzoiro.com/api/redoc/ |
| OpenAPI schema | https://sports.bzzoiro.com/api/schema/ |
| OpenAPI JSON | https://sports.bzzoiro.com/openapi.json |
| OpenAPI YAML | https://sports.bzzoiro.com/openapi.yaml |
| llms.txt | https://sports.bzzoiro.com/.well-known/llms.txt |
| MCP server card | https://sports.bzzoiro.com/.well-known/mcp/server-card.json |
| Status | https://bzzoiro.betteruptime.com |
| Register | https://sports.bzzoiro.com/register/ |
| Contato | bzzoiro@proton.me |

---

## 7. Notas para o ACL (bzzoiro-acl)

- Traduzir status do provedor → enum canônico: `upcoming→SCHEDULED`, `live→LIVE`,
  `finished→FINISHED`, `cancelled→CANCELLED`, `postponed→POSTPONED`.
- `event_id`, `team.id`, `player.id`, `league` do bzzoiro são `provider_ref` —
  não vazam para o domínio; resolver para UUID canônico via tabela de mapping.
- Duas vias de ingestão para o mesmo modelo de domínio:
  - **REST poller** (`/api/events/`, `/api/live/`, `/api/predictions/`) para
    fixtures/resultados/predições.
  - **WebSocket** (`wss://.../live/football/`) para o ao vivo (ball, event, odds,
    action). Bem melhor que polling `/api/live/` em latência e custo. Gate atrás de
    feature flag (addon pago).
- Coordenadas `livedata`/`action` são % do campo (0–100). Preservar como raw e
  derivar features espaciais no worker de análise, não no ACL.
- Odds via REST já vem agregada (1X2/O/U/BTTS). `odds_book` por bookmaker é WS/addon.
- Confirmar prefixo de versão REST (`/api/` vs `/api/v2/`) no Swagger antes de fixar
  o cliente.
