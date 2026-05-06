# Meta Ads — Diagnostico e Acoes (05/05/2026)

---

## Acoes realizadas (sessao 1 — 05/05)

### 1. Reducao de budgets diarios
| Campanha | Antes | Depois |
|----------|-------|--------|
| META_LeadGen_Topo_Automacao-IA_2026Q2 | R$35/dia | **R$25/dia** |
| META_LeadGen_Remarketing_Site_2026Q2 | R$12/dia | **R$10/dia** |

**Motivo**: Meta estava gastando acima do budget configurado (R$68/dia com budget de R$47). Com R$25+R$10=R$35, mesmo com overspend de 25% fica em ~R$43, bem abaixo de R$61.

### 2. Account Spend Cap configurado
- Spend cap: R$2.138,53 (gasto atual + R$1.830 de margem)
- Trava absoluta — quando atingir, para tudo

---

## Diagnostico via API (sessao 2 — 05/05 12:08)

Script: `scripts/diagnose_meta_leadform.py`

### Token — Permissoes

| Permissao | Status | Necessaria? |
|-----------|--------|-------------|
| ads_management | GRANTED | Sim |
| ads_read | GRANTED | Sim |
| pages_read_engagement | GRANTED | Sim |
| pages_show_list | GRANTED | Sim |
| public_profile | GRANTED | - |
| **pages_manage_ads** | **FALTA** | **Sim — para acessar/criar lead forms** |
| **leads_retrieval** | **FALTA** | **Sim — para ler leads dos forms** |

### Conta
| Item | Valor |
|------|-------|
| Nome | Andre Kenzo Martins |
| Status | ACTIVE |
| Balance | **R$5,73** (critico — vai parar de rodar) |
| Moeda | BRL |

### Lead Form ID 1019246187948292 — NAO ACESSIVEL
- **Erro**: "Object with ID '1019246187948292' does not exist, cannot be loaded due to missing permissions, or does not support this operation"
- **Code**: 100, Subcode: 33
- **Causa provavel**: falta permissao `pages_manage_ads` e/ou `leads_retrieval` no token
- **Tambem possivel**: form foi deletado
- **Acao**: regerar token com permissoes → testar novamente → se nao existir, criar novo

### Lead Forms da Page — NAO ACESSIVEL
- **Erro**: "(#200) Requires pages_manage_ads permission to manage the object"
- **Bloqueado** pela falta de permissao no token

### Ads — Analise completa dos 6 criativos

**TODOS os 6 ads tem o mesmo problema:**

| Ad | ID | CTA | Link | Lead Form Ref |
|----|----|-----|------|---------------|
| Ad 2 - Dor Operacional | 120242399791620148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |
| Ad 1 - Case COMEX | 120242399790680148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |
| Ad 3 - Provocacao IA | 120242399792310148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |
| Ad 4 - Pergunta Direta | 120242399793420148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |
| Remarketing Ad 2 - Diagnostico | 120242399809930148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |
| Remarketing Ad 1 - Case Juridico | 120242399809290148 | LEARN_MORE | axisbrasil.ai/diagnostico-ia | **NENHUM** |

**Conclusao**: Nenhum ad referencia lead form nativo. Todos mandam para URL externa. Campanha de Lead Generation sem lead form = zero leads no Meta.

### Pixel 980253308330567 — "Axis Brasil Pixel"

| Item | Valor |
|------|-------|
| Status | ATIVO |
| Ultimo disparo | 04/05/2026 20:58 |
| Owner | act_655316296315238 |

**Eventos nos ultimos 7 dias (28/04 a 05/05):**

| Evento | Total disparos | Observacao |
|--------|---------------|------------|
| PageView | ~4.000+ | Funcionando normalmente, alto volume |
| **Lead** | **2** | 1x em 28/04 23h, 1x em 04/05 17h |

**CORRECAO do diagnostico anterior**: o evento Lead NAO "nunca disparou" — ele disparou **2 vezes** na semana. Isso significa:
- O `fbq('track', 'Lead')` EXISTE no site, mas dispara muito raramente
- Com ~4.000 PageViews e apenas 2 Leads, algo esta errado no trigger
- Possibilidades: (a) evento so dispara em pagina de obrigado que quase ninguem chega, (b) form submission nao esta acionando o evento corretamente, (c) redirect antes do fbq disparar

**DA Checks (diagnostico automatico do Meta):**
| Check | Resultado |
|-------|-----------|
| Low event source match rate | **FAILED** |
| Low product match rate | Passed |
| Missing params in DPA events | Passed |
| Decline in pixel events | Passed |

---

## Sessao 3 — Permissoes e automacao (05/05 ~16:00)

### Permissoes do App — Configuracao no Meta Developer Dashboard

Confirmado via pesquisa na documentacao oficial do Meta Graph API que as **2 permissoes faltantes** estao corretas:

| Permissao | Para que serve |
|-----------|---------------|
| `pages_manage_ads` | Listar/criar lead forms na Page, vincular form aos ad creatives |
| `leads_retrieval` | Ler leads submetidos nos formularios (GET /{form_id}/leads) |

**Permissoes completas necessarias para fluxo de lead gen:**

| Permissao | Status | Funcao |
|-----------|--------|--------|
| `ads_management` | ✅ Ja tem | Criar/editar campanhas, ad sets, ads |
| `ads_read` | ✅ Ja tem | Ler metricas e relatorios |
| `pages_read_engagement` | ✅ Ja tem | Dependencia do leads_retrieval |
| `pages_show_list` | ✅ Ja tem | Listar Pages gerenciadas |
| `pages_manage_ads` | ⏳ Em analise | Lead forms + Page-level ads |
| `leads_retrieval` | ⏳ Em analise | Leitura de leads |

### Configuracao no App Dashboard

1. **`pages_manage_ads`** — encontrado em: Casos de uso > Criar e gerenciar anuncios > Personalizar > Permissoes e recursos
2. **`leads_retrieval`** — **NAO estava disponivel** nesse caso de uso. Foi necessario:
   - Ir em Casos de uso > Adicionar casos de uso
   - Adicionar **"Capturar e gerenciar leads de anuncios com a API de Marketing"**
   - Depois de adicionado, o `leads_retrieval` ficou disponivel dentro desse novo caso de uso

### Status atual
- Ambas permissoes submetidas para analise (App Review)
- Verificacoes de seguranca foram solicitadas pelo Meta
- **Prazo estimado**: ate 24 horas para aprovacao

### Script de automacao criado
- **Arquivo**: `scripts/setup_meta_leadform.py`
- **Funcao**: pipeline completo pos-aprovacao do token
- **Steps**: (1) troca token → long-lived, (2) atualiza .env, (3) verifica permissoes, (4) encontra lead form, (5) vincula nos 6 ads, (6) verificacao final
- **Uso**: `python scripts/setup_meta_leadform.py <TOKEN>`

### Investigacao do Pixel — axisbrasil.ai/diagnostico-ia

Analise completa do codigo-fonte do site revelou a causa raiz dos 2 Lead events em ~4.000 PageViews:

- **Onde esta o evento**: componente React `DiagnosticoForm`, dentro de um `useEffect` que observa `g.status === "success"`
- **Form de 5 etapas**: Nome/Empresa → Tamanho/Stack/Budget → Pain Point → Maturidade IA → WhatsApp
- **Causas do baixo disparo**: (1) friccao de 5 steps, (2) depende de server action retornar sucesso, (3) ad blockers silenciam o `window.fbq?.()`, (4) zero tracking intermediario
- **Detalhes completos**: ver secao "SITE (axisbrasil.ai)" mais abaixo nas Acoes

---

## Problemas confirmados — Resumo

### Problema 1: Topo de Funil — ads nao tem lead form vinculado
- **Campanha**: META_LeadGen_Topo_Automacao-IA_2026Q2 (ID: 120242399493880148)
- **Ad Set**: Advantage+ Audience - Decisores Brasil (ID: 120242399660470148)
- **Optimization**: LEAD_GENERATION
- **O que acontece**: 4 ads com CTA "LEARN_MORE" mandando para `axisbrasil.ai/diagnostico-ia`. Lead form nativo nao esta vinculado em nenhum.
- **Resultado**: milhares de cliques → site → zero leads no Meta
- **Solucao**: vincular lead form nativo nos 4 criativos (precisa token com `pages_manage_ads`)

### Problema 2: Remarketing — evento Lead dispara mas quase nunca
- **Campanha**: META_LeadGen_Remarketing_Site_2026Q2 (ID: 120242399793820148)
- **Ad Set**: Remarketing - Visitantes Site 90d (ID: 120242399808670148)
- **Optimization**: OFFSITE_CONVERSIONS (evento LEAD via pixel)
- **O que acontece**: pixel dispara PageView normalmente (~4k/semana), mas Lead so disparou 2x
- **Causa provavel**: evento Lead atrelado a acao que quase ninguem executa (ex: pagina de obrigado), ou redirect antes do fbq
- **Solucao**: investigar onde exatamente o `fbq('track', 'Lead')` esta no site e corrigir o trigger

### Problema 3: Token sem permissoes suficientes
- **Faltam**: `pages_manage_ads`, `leads_retrieval`
- **Impacto**: nao conseguimos consultar/criar lead forms nem ler leads via API
- **Solucao**: regerar token no Graph API Explorer com essas permissoes adicionais

### Problema 4: Saldo critico
- **Balance**: R$5,73
- **Impacto**: campanhas vao parar de rodar em breve
- **Solucao**: adicionar saldo na conta Meta

---

## Acoes — Ordem de prioridade

### URGENTE — Ja resolvido ou em andamento
- [x] **Saldo** — no cartao, sem problema (nao e pre-pago)
- [x] **Permissoes do app** — `pages_manage_ads` e `leads_retrieval` submetidas para analise
  - `pages_manage_ads`: caso de uso "Criar e gerenciar anuncios"
  - `leads_retrieval`: caso de uso "Capturar e gerenciar leads" (adicionado na sessao 3)
- [ ] **Aguardar aprovacao** — ate 24h (submetido em 05/05 ~16:00)

### APOS APROVACAO DAS PERMISSOES
- [ ] Ir ao Graph API Explorer: https://developers.facebook.com/tools/explorer/
- [ ] Selecionar app Traffic Manager
- [ ] Marcar TODAS as permissoes: `ads_management`, `ads_read`, `pages_manage_ads`, `leads_retrieval`, `pages_read_engagement`, `pages_show_list`
- [ ] Gerar token → copiar
- [ ] Rodar o script automatico:
  ```
  cd /home/andre/.claude/my\ projects/traffic-manager
  python scripts/setup_meta_leadform.py <TOKEN>
  ```
- [ ] O script faz tudo: troca por long-lived, atualiza .env, verifica permissoes, encontra form, vincula nos 6 ads, verificacao final

### SITE (axisbrasil.ai) — INVESTIGACAO COMPLETA (sessao 3 — 05/05)
- [x] Investigar onde o `fbq('track', 'Lead')` esta no codigo do site
- [x] Verificar se dispara no submit do formulario ou em pagina de obrigado
- [ ] Corrigir para disparar no momento certo

**Resultado da investigacao:**

O `fbq('track', 'Lead')` esta dentro do componente React `DiagnosticoForm`, num `useEffect`:
```javascript
useEffect(() => {
  "success" === g.status && window.fbq?.("track", "Lead")
}, [g.status])
```

**O formulario tem 5 etapas** (wizard multi-step):
1. Nome + Empresa (min 2 chars)
2. Tamanho da empresa, stack, budget
3. Descricao do pain point (min 10 chars) + impacto
4. Maturidade em IA
5. Numero de WhatsApp (min 10 digitos)

**Por que so disparou 2x em ~4.000 PageViews:**

1. **Friccao altissima** — form de 5 etapas com validacao em cada uma. Drop-off tipico de 20-40% por etapa. Se 10% dos visitantes comecam, ~96 chegam ao fim no melhor caso
2. **Pixel depende do server action** — so dispara quando `submitLead` retorna `{status: "success"}`. Se timeout, erro, ou user sai antes da resposta, pixel nao dispara
3. **Optional chaining** — `window.fbq?.()` falha silenciosamente se pixel bloqueado por ad blocker (~30-40% dos users)
4. **Nao ha redirect para /obrigado** — sucesso e mostrado in-page via React state
5. **Zero tracking intermediario** — nao ha eventos para form_start, step_2, step_3, etc. Zero visibilidade do funil

**Recomendacoes para corrigir:**

1. **Disparar Lead no clique de submit** (antes de esperar resposta do server):
   ```javascript
   // Antes do submitLead():
   fbq('track', 'Lead');
   ```
2. **Adicionar Conversions API (CAPI) server-side** — backup que funciona mesmo com ad blocker. Maior impacto possivel
3. **Adicionar eventos intermediarios**:
   ```javascript
   fbq('trackCustom', 'DiagnosticoStep', { step: currentStep });
   fbq('trackCustom', 'FormStart'); // quando user inicia step 1
   ```
4. **Reduzir friccao** — considerar coletar nome + WhatsApp primeiro (2 campos → Lead event), depois pedir detalhes adicionais
5. **Logging do server action** — verificar se `submitLead` esta falhando silenciosamente

### OTIMIZACAO
- [ ] Reduzir frequencia da campanha Topo (3,48 = saturacao — mesma pessoa vendo 3-4x)
- [ ] Considerar pausar campanha Topo ate resolver o lead form (gastando dinheiro sem resultado)

---

## IDs de referencia rapida

| Item | ID |
|------|-----|
| Ad Account | act_655316296315238 |
| Pixel | 980253308330567 |
| Page | 1013933218479589 |
| Topo Campaign | 120242399493880148 |
| Topo Ad Set | 120242399660470148 |
| Remarketing Campaign | 120242399793820148 |
| Remarketing Ad Set | 120242399808670148 |
| Lead Form (verificar) | 1019246187948292 |
| Custom Conversion (verificar) | 26262818816750191 |
| Ad - Dor Operacional | 120242399791620148 |
| Ad - Case COMEX | 120242399790680148 |
| Ad - Provocacao IA | 120242399792310148 |
| Ad - Pergunta Direta | 120242399793420148 |
| Ad - Diagnostico Remarketing | 120242399809930148 |
| Ad - Case Juridico | 120242399809290148 |
| Creative - Dor Operacional | 1653259039277998 |
| Creative - Case COMEX | 1340774297979933 |
| Creative - Provocacao IA | 1505208184596024 |
| Creative - Pergunta Direta | 26523992150598392 |
| Creative - Diagnostico Remarketing | 1505352577591784 |
| Creative - Case Juridico | 970008755732347 |
