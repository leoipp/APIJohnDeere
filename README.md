# API John Deere — Operations Center (Flask)

API Flask que autentica via OAuth2 com o John Deere Operations Center e expõe dados como endpoints REST para consumo por dashboards (Power BI) e integrações internas.

---

## Sumário

- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Como executar](#como-executar)
- [Fluxo de autenticação](#fluxo-de-autenticação)
- [Padrão dos endpoints](#padrão-dos-endpoints)
- [Rotas — Autenticação](#rotas--autenticação)
- [Rotas — Organizações](#rotas--organizações)
- [Rotas — Equipment](#rotas--equipment)
- [Rotas — Máquinas (telemetria)](#rotas--máquinas-telemetria)
- [Rotas — Assets](#rotas--assets)
- [Rotas — Mapas e Camadas](#rotas--mapas-e-camadas)
- [Rotas — Arquivos e TIMBERLINK](#rotas--arquivos-e-timberlink)
- [Rotas — Agronomia](#rotas--agronomia)
- [Rotas — Fazendas e Operadores](#rotas--fazendas-e-operadores)
- [Rotas — BI e Utilitários](#rotas--bi-e-utilitários)
- [Integração com Power BI](#integração-com-power-bi)
- [Deploy no Azure](#deploy-no-azure)

---

## Variáveis de ambiente

Crie o arquivo `variaveis_ambiente.json` na raiz do projeto (use `variaveis_ambiente_exemplo.json` como base):

```json
{
  "FLASK_SECRET_KEY": "chave-forte-e-aleatoria",
  "PORT": "5000",
  "DEERE_CLIENT_ID": "seu-client-id",
  "DEERE_CLIENT_SECRET": "seu-client-secret",
  "DEERE_REDIRECT_URI": "http://localhost:5000/auth/callback",
  "DEERE_OAUTH_ISSUER": "https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7",
  "DEERE_SCOPES": "ag1 ag2 ag3 org1 eq1 eq2 files offline_access",
  "DEERE_API_BASE_URL": "https://api.deere.com/platform",
  "HTTP_TIMEOUT_SECONDS": "120"
}
```

| Variável | Obrigatória | Padrão |
|---|---|---|
| `FLASK_SECRET_KEY` | Sim (produção) | `dev-secret-change-me` |
| `DEERE_CLIENT_ID` | Sim | — |
| `DEERE_CLIENT_SECRET` | Sim | — |
| `DEERE_REDIRECT_URI` | Não | `http://localhost:5000/auth/callback` |
| `DEERE_OAUTH_ISSUER` | Não | `https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7` |
| `DEERE_SCOPES` | Não | `ag1 org1 offline_access` |
| `DEERE_API_BASE_URL` | Não | `https://api.deere.com/platform` |
| `HTTP_TIMEOUT_SECONDS` | Não | `120` |
| `PORT` | Não | `5000` |

---

## Como executar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
python main.py
```

A API ficará disponível em `http://localhost:5000`.

---

## Fluxo de autenticação

O John Deere usa **OAuth2 Authorization Code Flow** com sessão server-side:

```
1. GET /auth/login          → redireciona para login John Deere
2. Usuário autoriza no portal John Deere
3. GET /auth/callback       → troca o code por tokens e salva na sessão
4. Todos os endpoints /api/* já funcionam (token renovado automaticamente)
```

O token de acesso é renovado automaticamente via `refresh_token` quando expira. Para invalidar a sessão, chame `GET /auth/logout`.

---

## Padrão dos endpoints

Todos os endpoints protegidos aceitam os query params abaixo:

| Param | Valores | Descrição |
|---|---|---|
| `raw` | `true` / `false` (padrão) | `true` retorna o JSON bruto da Deere; `false` retorna normalizado e plano |
| `startDate` | ISO 8601 ex: `2025-01-01T00:00:00Z` | Data de início (endpoints temporais) |
| `endDate` | ISO 8601 ex: `2025-12-31T23:59:59Z` | Data de fim (endpoints temporais) |

**Paginação:** feita automaticamente. A API segue todos os links `nextPage` da Deere e retorna tudo consolidado.

**Resposta normalizada padrão (listas):**
```json
{
  "total": 42,
  "values": [ { "id": "...", "name": "..." } ]
}
```

### Status dos endpoints

| Status | Significado |
|---|---|
| ✅ confirmado | Testado contra API Deere real, retornou dados |
| ❌ 403 | Restrição de conta ou permissão de aplicação no portal Deere |
| ⚠️ não testado | Implementado mas não validado com conta real |

> Endpoints marcados como ❌ continuam no código e repassam o erro original da Deere — podem funcionar com outros tipos de conta ou após aprovação no developer portal.

---

## Rotas — Autenticação

```
GET /auth/login              Inicia o fluxo OAuth2
GET /auth/callback           Callback do OAuth2 (não chamar diretamente)
GET /auth/status             Retorna se está autenticado e quando o token expira
GET /auth/refresh-token      Força renovação do access token
GET /auth/logout             Invalida a sessão local
GET /auth/token-info         Decodifica o JWT e mostra scopes concedidos vs solicitados
```

### Links diretos

| Ação | Link |
|---|---|
| Login | http://localhost:5000/auth/login |
| Status da sessão | http://localhost:5000/auth/status |
| Scopes do token | http://localhost:5000/auth/token-info |
| Logout | http://localhost:5000/auth/logout |

---

## Rotas — Organizações

Base: `http://localhost:5000/api/oc`

```
GET /organizations                  ✅ confirmado
GET /organizations/{id}             ✅ confirmado
GET /organizations/{id}/settings    ✅ confirmado
```

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Listar organizações | http://localhost:5000/api/oc/organizations |
| Organização 413958 | http://localhost:5000/api/oc/organizations/413958 |
| Configurações da org | http://localhost:5000/api/oc/organizations/413958/settings |
| Raw (bruto) | http://localhost:5000/api/oc/organizations?raw=true |

---

## Rotas — Equipment

Base: `http://localhost:5000/api/oc`

```
GET /organizations/{id}/equipment                           ✅ confirmado
GET /organizations/{id}/equipment-summary                   ✅ confirmado
GET /organizations/{id}/machines                            ✅ confirmado
GET /organizations/{id}/machines-summary                    ✅ confirmado
GET /equipmentTypes                                         ❌ 403 — restrito a contas OEM/parceiro
GET /equipmentISGTypes                                      ❌ 403 — restrito a contas OEM/parceiro
GET /equipmentModels/{serialNumber}                         ⚠️  não testado
GET /equipmentMakes/{makeId}/equipmentTypes/{typeId}/equipmentModels/{modelId}   ⚠️  não testado
GET /equipment/{id}                                         ⚠️  não testado
```

> **Nota sobre 403 em equipmentTypes / equipmentISGTypes:** esses endpoints são do catálogo global da Deere e exigem conta OEM ou de fabricante. Contas de operador recebem 403 mesmo com os scopes `eq1` e `eq2` presentes.

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Equipamentos | http://localhost:5000/api/oc/organizations/413958/equipment |
| Equipment summary | http://localhost:5000/api/oc/organizations/413958/equipment-summary |
| Só com telemática | http://localhost:5000/api/oc/organizations/413958/equipment-summary?only_telematics=true |
| Machines | http://localhost:5000/api/oc/organizations/413958/machines |
| Machines summary | http://localhost:5000/api/oc/organizations/413958/machines-summary |

---

## Rotas — Máquinas (telemetria)

Base: `http://localhost:5000/api/oc`

```
GET /machines/{id}/engineHours              ✅ confirmado
GET /machines/{id}/engineHours/latest       ✅ confirmado
GET /organizations/{id}/engine-hours        ✅ confirmado (horímetro consolidado de toda frota)
GET /machines/{id}/breadcrumbs              ✅ confirmado
GET /machines/{id}/locationHistory          ✅ confirmado
GET /machines/{id}/deviceStateReports       ✅ confirmado
GET /machines/{id}/hoursOfOperation         ✅ confirmado
GET /machines/{id}/fuelAndUtilization       ✅ confirmado
GET /machines/{id}/machineMeasurements      ✅ confirmado
GET /machines/{id}/harvesterHead            ✅ confirmado — medições de cabeçote colheitadeira florestal
```

> **Dica — `principalId` vs `id`:** máquinas transferidas entre organizações podem ter `id != principalId`. Para chamadas diretas, se `engineHours` retornar 404, tente usar o `principalId` da máquina no lugar do `id`.

> **`harvesterHead`** retorna medições StanForD de cabeçote: Volume, Grapple Count, Times (working/idle/moving/maintenance), Fuel Consumption e Machine Utilization. Usar com `?startDate=` e `?endDate=`.

### Links diretos (org 413958)

Substitua `{MACHINE_ID}` pelo ID numérico da máquina obtido em `/organizations/413958/machines-summary`.

| Endpoint | Link |
|---|---|
| Horímetro consolidado da frota | http://localhost:5000/api/oc/organizations/413958/engine-hours |
| Frota com arquivadas | http://localhost:5000/api/oc/organizations/413958/engine-hours?include_archived=true |
| Machines summary (para obter IDs) | http://localhost:5000/api/oc/organizations/413958/machines-summary |

Exemplos com `MACHINE_ID`:
```
http://localhost:5000/api/oc/machines/{MACHINE_ID}/engineHours/latest
http://localhost:5000/api/oc/machines/{MACHINE_ID}/hoursOfOperation?startDate=2025-01-01T00:00:00Z&endDate=2025-12-31T23:59:59Z
http://localhost:5000/api/oc/machines/{MACHINE_ID}/fuelAndUtilization?startDate=2025-01-01T00:00:00Z&endDate=2025-12-31T23:59:59Z
http://localhost:5000/api/oc/machines/{MACHINE_ID}/breadcrumbs?startDate=2025-12-01T00:00:00Z&endDate=2025-12-31T23:59:59Z
http://localhost:5000/api/oc/machines/{MACHINE_ID}/harvesterHead?startDate=2025-12-01T00:00:00Z&endDate=2025-12-31T23:59:59Z
```

---

## Rotas — Assets

Base: `http://localhost:5000/api/oc`

```
GET /assetCatalog                           ⚠️  não testado
GET /assets/{assetId}                       ⚠️  não testado
GET /organizations/{orgId}/assets           ⚠️  não testado
GET /assets/{assetId}/locations             ⚠️  não testado
```

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Catálogo de assets | http://localhost:5000/api/oc/assetCatalog |
| Assets da org | http://localhost:5000/api/oc/organizations/413958/assets |

---

## Rotas — Mapas e Camadas

Base: `http://localhost:5000/api/oc`

```
GET /fileResources/{fileResourceId}
GET /mapLayerSummaries/{mapLayerSummaryId}
GET /mapLayers/{mapLayerId}
GET /mapLayers/{mapLayerId}/fileResources
GET /organizations/{orgId}/fields/{fieldId}/mapLayerSummaries
```

---

## Rotas — Arquivos e TIMBERLINK

Base: `http://localhost:5000/api/oc`

```
GET /files                                          ✅ confirmado
GET /files/{id}                                     ✅ confirmado
GET /organizations/{orgId}/files                    ✅ confirmado
GET /organizations/{orgId}/files/stanford           ✅ confirmado — lista arquivos StanForD/TIMBERLINK
GET /files/{id}/download                            ✅ confirmado — download do binário (zip)
```

> **Arquivos TIMBERLINK:** a organização 413958 possui arquivos dos tipos `.hpr`, `.prd`, `.spi`, `.mom`, `.oin`, `.pin` gerados pelas máquinas florestais, empacotados em `.zip` com tipo `TIMBERLINK`. O endpoint `/stanford` lista todos com metadados (id, nome, tamanho, máquina de origem, data).
>
> **Download do conteúdo interno:** os zips contêm arquivos StanForD criptografados. A senha é entregue pelo endpoint `presignedDownload` da Deere, que requer aprovação do produto **TIMBERLINK** no [developer.deere.com](https://developer.deere.com) para a aplicação. A listagem e o download do zip funcionam; a decriptação aguarda essa aprovação.

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Arquivos StanForD/TIMBERLINK — dez/2025 | http://localhost:5000/api/oc/organizations/413958/files/stanford?startDate=2025-12-30&endDate=2025-12-30 |
| Arquivos StanForD — ano completo 2025 | http://localhost:5000/api/oc/organizations/413958/files/stanford?startDate=2025-01-01&endDate=2025-12-31&itemLimit=500 |
| Metadados de arquivo específico | http://localhost:5000/api/oc/files/57875288154 |
| Metadados raw (estrutura Deere) | http://localhost:5000/api/oc/files/57875288154?raw=true |
| Download do zip | http://localhost:5000/api/oc/files/57875288154/download |

---

## Rotas — Agronomia

Base: `http://localhost:5000/api/agro`

```
GET /chemicals
GET /chemicals/{id}
GET /organizations/{orgId}/chemicals
GET /organizations/{orgId}/chemicals/{id}

GET /activeIngredients

GET /fertilizers
GET /fertilizers/{id}
GET /organizations/{orgId}/fertilizers
GET /organizations/{orgId}/fertilizers/{id}

GET /varieties
GET /varieties/{id}
GET /organizations/{orgId}/varieties
GET /organizations/{orgId}/varieties/{id}

GET /organizations/{orgId}/tankMixes
GET /organizations/{orgId}/tankMixes/{id}

GET /organizations/{orgId}/dryBlends
GET /organizations/{orgId}/dryBlends/{id}

GET /organizations/{orgId}/productCompanies
```

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Defensivos globais | http://localhost:5000/api/agro/chemicals |
| Defensivos da org | http://localhost:5000/api/agro/organizations/413958/chemicals |
| Ingredientes ativos | http://localhost:5000/api/agro/activeIngredients |
| Fertilizantes | http://localhost:5000/api/agro/fertilizers |
| Fertilizantes da org | http://localhost:5000/api/agro/organizations/413958/fertilizers |
| Variedades | http://localhost:5000/api/agro/varieties |
| Variedades da org | http://localhost:5000/api/agro/organizations/413958/varieties |
| Tank mixes | http://localhost:5000/api/agro/organizations/413958/tankMixes |
| Dry blends | http://localhost:5000/api/agro/organizations/413958/dryBlends |
| Empresas de produtos | http://localhost:5000/api/agro/organizations/413958/productCompanies |

---

## Rotas — Fazendas e Operadores

Base: `http://localhost:5000/api/oc`

```
GET /organizations/{orgId}/operators                            ✅ confirmado
GET /organizations/{orgId}/operators/{operatorErid}             ⚠️  não testado
GET /organizations/{orgId}/farms                                ✅ confirmado
GET /organizations/{orgId}/farms/{farmId}                       ⚠️  não testado
GET /organizations/{orgId}/farms/{farmId}/clients               ⚠️  não testado
GET /organizations/{orgId}/fieldOperations                      ⚠️  não testado
GET /organizations/{orgId}/fieldOperations/harvest              ⚠️  não testado
GET /organizations/{orgId}/fieldOperations/{operationId}        ⚠️  não testado
```

### Links diretos (org 413958)

| Endpoint | Link |
|---|---|
| Operadores | http://localhost:5000/api/oc/organizations/413958/operators |
| Fazendas | http://localhost:5000/api/oc/organizations/413958/farms |
| Operações de campo | http://localhost:5000/api/oc/organizations/413958/fieldOperations |
| Colheitas | http://localhost:5000/api/oc/organizations/413958/fieldOperations/harvest |

---

## Rotas — BI e Utilitários

```
GET /api/bi/fleet?organization_id={id}   ✅ confirmado — frota formatada para Power BI
GET /api/oc/proxy?path={path}            ✅ confirmado — GET genérico autenticado para qualquer endpoint Deere
GET /api/oc/discovery/ids?path={path}    ✅ confirmado — descobre IDs automaticamente
GET /health                              ✅ confirmado — healthcheck
```

### Links diretos

| Endpoint | Link |
|---|---|
| Frota para BI | http://localhost:5000/api/bi/fleet?organization_id=413958 |
| Healthcheck | http://localhost:5000/health |
| Proxy — organizations | http://localhost:5000/api/oc/proxy?path=/organizations/413958 |
| Proxy — fields | http://localhost:5000/api/oc/proxy?path=/organizations/413958/fields |
| Discovery de IDs | http://localhost:5000/api/oc/discovery/ids?path=/organizations/413958/farms |

---

## Integração com Power BI

### Pré-requisito

A API precisa estar acessível pelo Power BI. Em desenvolvimento use `localhost:5000`. Em produção use a URL do Azure (ver seção abaixo).

**Importante:** O Power BI Desktop consegue chamar APIs REST diretamente via Power Query (M). O Power BI Service (nuvem) exige que a fonte de dados esteja publicada em uma URL acessível — não aceita `localhost`.

---

### Passo a passo no Power BI Desktop

#### 1. Autenticar uma vez no navegador

Antes de conectar o Power BI, faça login manualmente no navegador:

```
http://localhost:5000/auth/login
```

Autorize no portal John Deere. A sessão fica salva no servidor Flask enquanto ele estiver rodando.

#### 2. Criar uma fonte de dados Web no Power BI

1. Abra o **Power BI Desktop**
2. Clique em **Obter Dados → Web**
3. Insira a URL do endpoint desejado, por exemplo:
   ```
   http://localhost:5000/api/oc/organizations/413958/equipment-summary
   ```
4. Clique em **OK → Conectar**
5. Power BI vai carregar o JSON. Expanda o campo `values` para ver a tabela.

#### 3. Usar Power Query (M) para múltiplos endpoints

No Power BI, abra o **Editor do Power Query → Nova Consulta → Consulta em Branco** e use:

```m
let
    url = "http://localhost:5000/api/oc/organizations/413958/equipment-summary",
    resposta = Json.Document(Web.Contents(url)),
    valores = resposta[values],
    tabela = Table.FromList(valores, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    expandida = Table.ExpandRecordColumn(tabela, "Column1",
        {"id", "name", "serial_number", "make_name", "model_name",
         "type_name", "telematics_capable", "archived", "organization_id"})
in
    expandida
```

#### 4. Atualização agendada com parâmetros de data

```m
let
    startDate = "2025-01-01T00:00:00Z",
    endDate   = "2025-12-31T23:59:59Z",
    machineId = "SEU_MACHINE_ID",
    url = "http://localhost:5000/api/oc/machines/" & machineId
          & "/hoursOfOperation?startDate=" & startDate & "&endDate=" & endDate,
    resposta = Json.Document(Web.Contents(url)),
    valores = resposta[values],
    tabela = Table.FromList(valores, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    expandida = Table.ExpandRecordColumn(tabela, "Column1", {"date", "hours", "unit"})
in
    expandida
```

#### 5. Endpoints recomendados como tabelas no Power BI

| Tabela no Power BI | URL |
|---|---|
| Frota | http://localhost:5000/api/bi/fleet?organization_id=413958 |
| Horímetro por organização | http://localhost:5000/api/oc/organizations/413958/engine-hours |
| Horas de operação | `http://localhost:5000/api/oc/machines/{id}/hoursOfOperation?startDate=...` |
| Combustível e utilização | `http://localhost:5000/api/oc/machines/{id}/fuelAndUtilization?startDate=...` |
| Localização (breadcrumbs) | `http://localhost:5000/api/oc/machines/{id}/breadcrumbs?startDate=...` |
| Arquivos TIMBERLINK (listagem) | http://localhost:5000/api/oc/organizations/413958/files/stanford?startDate=2025-01-01&endDate=2025-12-31&itemLimit=500 |
| Operadores | http://localhost:5000/api/oc/organizations/413958/operators |
| Fazendas | http://localhost:5000/api/oc/organizations/413958/farms |

---

## Deploy no Azure

### Opção recomendada: Azure App Service

#### 1. Preparar o projeto

```bash
pip freeze > requirements.txt
```

Comando de startup:
```
gunicorn --bind=0.0.0.0:8000 --timeout 120 main:app
```

#### 2. Criar o App Service no Azure

```bash
az login
az group create --name rg-johndeere-api --location brazilsouth
az appservice plan create --name plan-johndeere-api --resource-group rg-johndeere-api --sku B1 --is-linux
az webapp create --name johndeere-api-empresa --resource-group rg-johndeere-api --plan plan-johndeere-api --runtime "PYTHON:3.11"
```

#### 3. Configurar as variáveis de ambiente no Azure

```bash
az webapp config appsettings set \
  --name johndeere-api-empresa \
  --resource-group rg-johndeere-api \
  --settings \
    FLASK_SECRET_KEY="chave-forte-aleatoria-producao" \
    DEERE_CLIENT_ID="seu-client-id" \
    DEERE_CLIENT_SECRET="seu-client-secret" \
    DEERE_REDIRECT_URI="https://johndeere-api-empresa.azurewebsites.net/auth/callback" \
    DEERE_SCOPES="ag1 ag2 ag3 org1 eq1 eq2 files offline_access" \
    DEERE_API_BASE_URL="https://api.deere.com/platform" \
    HTTP_TIMEOUT_SECONDS="120"
```

> **Atenção:** Após alterar o `DEERE_REDIRECT_URI`, atualize também o redirect URI cadastrado no portal de desenvolvedores John Deere.

#### 4. Fazer deploy

```bash
az webapp up --name johndeere-api-empresa --resource-group rg-johndeere-api --runtime "PYTHON:3.11"
```

#### 5. Considerações de segurança para produção

- Adicione autenticação no App Service via **Azure Active Directory** (Entra ID)
- Ou use **Azure API Management** como gateway com chave de API
- Ative **HTTPS Only** no App Service (já ativo por padrão)
- Use **Azure Key Vault** para armazenar `FLASK_SECRET_KEY` e `DEERE_CLIENT_SECRET`
- Configure **sessões persistentes** (ex: Redis Cache do Azure) para que o token OAuth não seja perdido entre reinicializações
