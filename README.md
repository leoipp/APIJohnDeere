# API John Deere (Flask)

API Flask para autenticar via OAuth2 no John Deere e consumir o endpoint de organizacoes do Operations Center.

## Endpoints

- `GET /` resumo da API
- `GET /health` healthcheck
- `GET /auth/login` inicia OAuth2
- `GET /auth/callback` callback OAuth2
- `GET /auth/refresh-token` renova access token
- `GET /auth/logout` limpa sessao
- `GET /auth/status` status da autenticacao
- `GET /api/oc/organizations` lista organizacoes (protegido)
- `GET /api/oc/machines/{id}/engineHour` consulta horimetro da maquina (protegido)
- `GET /api/oc/equipment/{id}` consulta equipamento por id (protegido)
- `GET /api/oc/equipmentMakes` lista marcas de equipamento (protegido)
- `GET /api/oc/equipmentMakes/{equipmentMakeId}/equipmentTypes` lista tipos por marca (protegido)
- `GET /api/oc/equipmentMakes/{equipmentMakeId}/equipmentTypes/{equipmentTypeId}/equipmentModels` lista modelos por tipo (protegido)
- `GET /api/oc/equipmentMakes/{equipmentMakeId}/equipmentTypes/{equipmentTypeId}/equipmentModels/{equipmentModelId}` consulta modelo por ids (protegido)
- `GET /api/oc/organizations/{org_id}/machines` lista maquinas por organizacao (protegido)
- `GET /api/oc/proxy?path=/...` GET generico para endpoints da plataforma (protegido)
- `GET /api/oc/discovery/ids?path=/...&path=/...` descobre IDs automaticamente em multiplos paths (protegido)
- `GET /api/oc/discovery/equipment-catalog` descobre em cadeia make/type/model (protegido)

## Variaveis de ambiente

- `FLASK_SECRET_KEY` chave da sessao Flask (obrigatoria em producao)
- `DEERE_CLIENT_ID` client id da app John Deere
- `DEERE_CLIENT_SECRET` client secret da app John Deere
- `DEERE_REDIRECT_URI` default: `http://localhost:5000/auth/callback`
- `DEERE_OAUTH_ISSUER` default: `https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7`
- `DEERE_SCOPES` default: `ag1 org1 offline_access`
- `DEERE_API_BASE_URL` default: `https://sandboxapi.deere.com/platform`
- `HTTP_TIMEOUT_SECONDS` default: `20`
- `PORT` default: `5000`

## Como executar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Configure as variaveis e rode:

```bash
python main.py
```

## Fluxo rapido

1. Acesse `GET /auth/login`
2. Autorize no portal John Deere
3. O callback salva tokens na sessao
4. Chame `GET /api/oc/organizations`
5. Ou chame `GET /api/oc/machines/{id}/engineHour`
