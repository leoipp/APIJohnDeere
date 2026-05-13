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
- [Rotas — Arquivos](#rotas--arquivos)
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
  "DEERE_SCOPES": "ag1 org1 eq1 eq2 offline_access",
  "DEERE_API_BASE_URL": "https://api.deere.com/platform",
  "HTTP_TIMEOUT_SECONDS": "20"
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
| `HTTP_TIMEOUT_SECONDS` | Não | `20` |
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

### Status dos endpoints testados em produção

| Status | Significado |
|---|---|
| ✅ confirmado | Testado contra API Deere real, retornou 200 |
| ❌ 403 | Retorna 403 — restrição de conta ou endpoint OEM/parceiro |
| ⚠️ não testado | Implementado mas não validado com conta real |

> Endpoints marcados como ❌ continuam no código e repassam o erro original da Deere, pois podem funcionar com outros tipos de conta.

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

### Teste rápido

```bash
# Verificar status
curl http://localhost:5000/auth/status

# Resposta esperada (não autenticado)
{"authenticated": false, "expires_at": null, "has_refresh_token": false}

# Inspecionar scopes do token (útil para diagnóstico de 403)
curl http://localhost:5000/auth/token-info
# Resposta: {"sub": "...", "scopes_granted": ["ag1","org1","eq1","eq2","offline_access"], "missing_scopes": []}
```

---

## Rotas — Organizações

Base: `http://localhost:5000/api/oc`

```
GET /organizations                  ✅ confirmado
GET /organizations/{id}             ✅ confirmado
GET /organizations/{id}/settings    ✅ confirmado
```

### Exemplos

```bash
# Listar todas as organizações
curl http://localhost:5000/api/oc/organizations

# Buscar organização específica
curl http://localhost:5000/api/oc/organizations/413958

# Configurações da organização
curl http://localhost:5000/api/oc/organizations/413958/settings

# Retorno bruto (sem normalização)
curl "http://localhost:5000/api/oc/organizations?raw=true"
```

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

> **Nota sobre 403 em equipmentTypes / equipmentISGTypes:** esses endpoints são do catálogo global da Deere e exigem conta OEM ou de fabricante. Contas de operador (fazenda/empresa) recebem 403 mesmo com os scopes `eq1` e `eq2` presentes no token. Isso é uma restrição de tipo de conta, não de configuração.

### Exemplos

```bash
# Listar equipamentos da organização (confirmados ✅)
curl "http://localhost:5000/api/oc/organizations/413958/equipment"
curl "http://localhost:5000/api/oc/organizations/413958/equipment-summary?only_telematics=true"
curl "http://localhost:5000/api/oc/organizations/413958/equipment-summary?include_archived=true"
curl "http://localhost:5000/api/oc/organizations/413958/machines-summary"

# Catálogo global — apenas contas OEM (retorna 403 para operadores)
curl http://localhost:5000/api/oc/equipmentTypes
curl http://localhost:5000/api/oc/equipmentISGTypes

# Buscar modelo pelo número de série
curl http://localhost:5000/api/oc/equipmentModels/1RW8500RPFE123456

# Buscar modelo pela hierarquia make/type/model
curl "http://localhost:5000/api/oc/equipmentMakes/2/equipmentTypes/1/equipmentModels/45"

# Buscar equipamento por ID (ISG)
curl http://localhost:5000/api/oc/equipment/abc123
```

---

## Rotas — Máquinas (telemetria)

Base: `http://localhost:5000/api/oc`

```
GET /machines/{id}/engineHours              ✅ confirmado
GET /machines/{id}/engineHours/latest       ✅ confirmado
GET /machines/{id}/breadcrumbs              ✅ confirmado
GET /machines/{id}/locationHistory          ✅ confirmado
GET /machines/{id}/deviceStateReports       ✅ confirmado
GET /machines/{id}/hoursOfOperation         ✅ confirmado
GET /machines/{id}/machineMeasurements      ⚠️  reativado via ISG (testar)
GET /organizations/{id}/engine-hours        ✅ confirmado (horímetro consolidado de toda frota)
```

> **Dica — `principalId` vs `id`:** máquinas transferidas entre organizações podem ter `id != principalId`. O endpoint `/engine-hours` por organização tenta automaticamente o `principalId` como fallback. Para chamadas diretas, se `engineHours` retornar 404, tente usar o `principalId` da máquina no lugar do `id`.

### Exemplos

```bash
MACHINE_ID="1396548"

# Histórico completo de horímetro
curl http://localhost:5000/api/oc/machines/$MACHINE_ID/engineHours

# Última leitura de horímetro
curl http://localhost:5000/api/oc/machines/$MACHINE_ID/engineHours/latest

# Trilha GPS (breadcrumbs) — período específico
curl "http://localhost:5000/api/oc/machines/$MACHINE_ID/breadcrumbs?startDate=2025-01-01T00:00:00Z&endDate=2025-01-31T23:59:59Z"

# Histórico de localização
curl "http://localhost:5000/api/oc/machines/$MACHINE_ID/locationHistory?startDate=2025-01-01T00:00:00Z"

# Relatórios de estado do dispositivo
curl "http://localhost:5000/api/oc/machines/$MACHINE_ID/deviceStateReports?startDate=2025-05-01T00:00:00Z"

# Horas de operação diárias
curl "http://localhost:5000/api/oc/machines/$MACHINE_ID/hoursOfOperation?startDate=2025-01-01T00:00:00Z&endDate=2025-03-31T23:59:59Z"

# Medições da máquina (nível de combustível, temperatura, etc.)
curl http://localhost:5000/api/oc/machines/$MACHINE_ID/machineMeasurements
curl "http://localhost:5000/api/oc/machines/$MACHINE_ID/machineMeasurements?raw=true"

# Consolidado de horímetro por organização (todas as máquinas com telemática)
curl http://localhost:5000/api/oc/organizations/413958/engine-hours
curl "http://localhost:5000/api/oc/organizations/413958/engine-hours?include_archived=true"
```

---

## Rotas — Assets

Base: `http://localhost:5000/api/oc`

```
GET /assetCatalog
GET /assets/{assetId}
GET /organizations/{orgId}/assets
GET /assets/{assetId}/locations
```

### Exemplos

```bash
ORG_ID="413958"
ASSET_ID="asset456"

# Catálogo de tipos de asset
curl http://localhost:5000/api/oc/assetCatalog

# Asset específico
curl http://localhost:5000/api/oc/assets/$ASSET_ID

# Assets de uma organização
curl http://localhost:5000/api/oc/organizations/$ORG_ID/assets

# Histórico de localização do asset
curl http://localhost:5000/api/oc/assets/$ASSET_ID/locations

# Com filtro de data
curl "http://localhost:5000/api/oc/assets/$ASSET_ID/locations?startDate=2025-01-01T00:00:00Z&endDate=2025-06-30T23:59:59Z"
```

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

### Exemplos

```bash
ORG_ID="413958"
FIELD_ID="field789"
LAYER_ID="layer001"

# Recurso de arquivo
curl http://localhost:5000/api/oc/fileResources/res001

# Sumário de camada de mapa
curl http://localhost:5000/api/oc/mapLayerSummaries/summary001

# Camada de mapa
curl http://localhost:5000/api/oc/mapLayers/$LAYER_ID

# Arquivos de uma camada
curl http://localhost:5000/api/oc/mapLayers/$LAYER_ID/fileResources

# Sumários de camadas de um campo
curl http://localhost:5000/api/oc/organizations/$ORG_ID/fields/$FIELD_ID/mapLayerSummaries
```

---

## Rotas — Arquivos

Base: `http://localhost:5000/api/oc`

```
GET /files
GET /files/{id}
GET /organizations/{orgId}/files
```

### Exemplos

```bash
ORG_ID="413958"

# Todos os arquivos
curl http://localhost:5000/api/oc/files

# Com filtro temporal
curl "http://localhost:5000/api/oc/files?startDate=2025-01-01T00:00:00Z"

# Arquivo específico
curl http://localhost:5000/api/oc/files/file001

# Arquivos da organização
curl http://localhost:5000/api/oc/organizations/$ORG_ID/files
```

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

### Exemplos

```bash
ORG_ID="413958"

# Defensivos globais
curl http://localhost:5000/api/agro/chemicals

# Defensivos da organização
curl http://localhost:5000/api/agro/organizations/$ORG_ID/chemicals

# Defensivo específico
curl http://localhost:5000/api/agro/chemicals/chem001

# Ingredientes ativos (ISG)
curl http://localhost:5000/api/agro/activeIngredients

# Fertilizantes
curl http://localhost:5000/api/agro/fertilizers
curl http://localhost:5000/api/agro/organizations/$ORG_ID/fertilizers

# Variedades
curl http://localhost:5000/api/agro/varieties
curl http://localhost:5000/api/agro/organizations/$ORG_ID/varieties

# Caldas (tank mixes)
curl http://localhost:5000/api/agro/organizations/$ORG_ID/tankMixes

# Misturas secas (dry blends)
curl http://localhost:5000/api/agro/organizations/$ORG_ID/dryBlends

# Empresas de produtos
curl http://localhost:5000/api/agro/organizations/$ORG_ID/productCompanies

# Retorno bruto em qualquer endpoint
curl "http://localhost:5000/api/agro/chemicals?raw=true"
```

---

## Rotas — Fazendas e Operadores

Base: `http://localhost:5000/api/oc`

```
GET /organizations/{orgId}/operators
GET /organizations/{orgId}/operators/{operatorErid}

GET /organizations/{orgId}/farms
GET /organizations/{orgId}/farms/{farmId}
GET /organizations/{orgId}/farms/{farmId}/clients
```

### Exemplos

```bash
ORG_ID="413958"
FARM_ID="farm001"
OPERATOR_ERID="op-erid-001"

# Operadores da organização
curl http://localhost:5000/api/oc/organizations/$ORG_ID/operators

# Operador específico
curl http://localhost:5000/api/oc/organizations/$ORG_ID/operators/$OPERATOR_ERID

# Fazendas
curl http://localhost:5000/api/oc/organizations/$ORG_ID/farms

# Fazenda específica
curl http://localhost:5000/api/oc/organizations/$ORG_ID/farms/$FARM_ID

# Clientes de uma fazenda
curl http://localhost:5000/api/oc/organizations/$ORG_ID/farms/$FARM_ID/clients
```

---

## Rotas — BI e Utilitários

```
GET /api/bi/fleet?organization_id={id}   Frota formatada para BI
GET /api/oc/proxy?path={path}            GET genérico autenticado para qualquer endpoint Deere
GET /api/oc/discovery/ids?path={path}    Descobre IDs automaticamente em um ou mais paths
GET /health                              Healthcheck
```

### Exemplos

```bash
# Frota para BI (retorna lista plana pronta para importar)
curl "http://localhost:5000/api/bi/fleet?organization_id=413958"

# Proxy genérico — útil para explorar endpoints não mapeados
curl "http://localhost:5000/api/oc/proxy?path=/organizations/413958/fields"

# Discovery — extrai todos os IDs de múltiplos paths
curl "http://localhost:5000/api/oc/discovery/ids?path=/organizations&path=/organizations/413958/farms"

# Healthcheck
curl http://localhost:5000/health
```

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

Para buscar dados com filtro temporal, parametrize as datas no Power Query:

```m
let
    startDate = "2025-01-01T00:00:00Z",
    endDate   = "2025-12-31T23:59:59Z",
    machineId = "abc123",
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
| Frota | `/api/bi/fleet?organization_id={id}` |
| Horímetro por máquina | `/api/oc/machines/{id}/engineHours/latest` |
| Horímetro por organização | `/api/oc/organizations/{id}/engine-hours` |
| Horas de operação | `/api/oc/machines/{id}/hoursOfOperation?startDate=...` |
| Localização (breadcrumbs) | `/api/oc/machines/{id}/breadcrumbs?startDate=...` |
| Assets | `/api/oc/organizations/{id}/assets` |
| Fazendas | `/api/oc/organizations/{id}/farms` |
| Operadores | `/api/oc/organizations/{id}/operators` |
| Defensivos | `/api/agro/organizations/{id}/chemicals` |
| Fertilizantes | `/api/agro/organizations/{id}/fertilizers` |
| Variedades | `/api/agro/organizations/{id}/varieties` |

---

## Deploy no Azure

### Opção recomendada: Azure App Service

#### 1. Preparar o projeto

Crie o arquivo `requirements.txt` se não existir:

```bash
pip freeze > requirements.txt
```

Crie o `startup.txt` ou configure o comando de startup no App Service:

```
gunicorn --bind=0.0.0.0:8000 --timeout 120 main:app
```

Instale o gunicorn:

```bash
pip install gunicorn
pip freeze > requirements.txt
```

#### 2. Criar o App Service no Azure

```bash
# Login no Azure CLI
az login

# Criar grupo de recursos
az group create --name rg-johndeere-api --location brazilsouth

# Criar App Service Plan (B1 é suficiente para início)
az appservice plan create \
  --name plan-johndeere-api \
  --resource-group rg-johndeere-api \
  --sku B1 --is-linux

# Criar o Web App
az webapp create \
  --name johndeere-api-empresa \
  --resource-group rg-johndeere-api \
  --plan plan-johndeere-api \
  --runtime "PYTHON:3.11"
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
    DEERE_SCOPES="ag1 org1 eq1 eq2 offline_access" \
    DEERE_API_BASE_URL="https://api.deere.com/platform" \
    HTTP_TIMEOUT_SECONDS="30"
```

> **Atenção:** Após alterar o `DEERE_REDIRECT_URI`, atualize também o redirect URI cadastrado no portal de desenvolvedores John Deere.

#### 4. Fazer deploy

```bash
# Via ZIP deploy
az webapp up \
  --name johndeere-api-empresa \
  --resource-group rg-johndeere-api \
  --runtime "PYTHON:3.11"
```

Ou configure CI/CD via GitHub Actions no portal Azure.

#### 5. Atualizar o Power BI para apontar para o Azure

Após o deploy, substitua `http://localhost:5000` pela URL do Azure em todas as consultas do Power BI:

```
https://johndeere-api-empresa.azurewebsites.net
```

Exemplo:
```
https://johndeere-api-empresa.azurewebsites.net/api/oc/organizations/413958/equipment-summary
```

#### Considerações de segurança para produção

- Adicione autenticação no App Service via **Azure Active Directory** (Entra ID) para que só usuários da empresa acessem a API
- Ou use **Azure API Management** como gateway com chave de API
- Ative **HTTPS Only** no App Service (já ativo por padrão)
- Use **Azure Key Vault** para armazenar `FLASK_SECRET_KEY` e `DEERE_CLIENT_SECRET`
- Configure **sessões persistentes** (ex: Redis Cache do Azure) para que o token OAuth não seja perdido entre reinicializações do servidor

```bash
# Habilitar HTTPS only (verificar se já está ativo)
az webapp update \
  --name johndeere-api-empresa \
  --resource-group rg-johndeere-api \
  --https-only true
```
