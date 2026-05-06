# AXIS BRASIL — LinkedIn Ads: O que falta

**Ultima atualizacao**: 2026-04-27

---

## Estado atual

| Item | Status | ID/Detalhe |
|------|--------|------------|
| Conta de anuncios | ATIVA (billing configurado) | 520407577 (BlossomBoost) |
| Moeda da conta | USD | $4/dia ≈ R$20/dia |
| Campaign Group | CRIADO | 924507643 — "LI_LeadGen_Decisores_Automacao-IA_2026Q2" |
| Campaign (Ad Set) | CRIADA | 671701263 — "Decisores B2B — Automacao e IA" (PAUSED) |
| Objetivo | LEAD_GENERATION | — |
| Budget | $4/dia, $2/click CPC | — |
| Targeting | PARCIAL | Brasil + pt_BR + Director/VP/CXO |
| 3 imagens | UPLOADED no CDN | URNs prontas (ver abaixo) |
| Ad Creatives (3 anuncios) | PENDENTE | Bloqueado por scope OAuth |
| Lead Gen Form | NAO CRIADO | Criar no Campaign Manager ou via API |

### Imagens ja uploaded (URNs validas)

```
axis_criativo_07_linkedin_comex.png      → urn:li:image:D4D10AQFMF5j7T-p6ug
axis_criativo_08_linkedin_cto.png        → urn:li:image:D4D10AQGFkBxsvR0r5A
axis_criativo_09_linkedin_estatistica.png → urn:li:image:D4D10AQHGHReR2Z1igA
```

Arquivos PNG em: `/mnt/d/Downloads_hd/axis_creatives_png/`

---

## Blockers pendentes

### 1. Aprovacao de produtos LinkedIn Developer (AGUARDANDO)

Solicitados em 27/04/2026, status "Pending review":

| Produto | Tier | Scope que libera | Para que serve |
|---------|------|------------------|----------------|
| **Share on LinkedIn** | Default | `w_member_social` | Criar dark posts (creatives) |
| **Lead Sync API** | Standard | `r_marketing_leads` | Capturar leads dos formularios |

**Quando aprovados**, seguir para o Passo 1 abaixo.

### 2. Community Management API (ALTERNATIVA)

Se "Share on LinkedIn" nao for suficiente para criar posts como organizacao:
- Criar um **segundo app LinkedIn Developer** com APENAS "Community Management API"
- Isso da scope `w_organization_social` (permite posts como org)
- O app atual nao aceita esse produto porque ele exige ser o unico produto no app

---

## Passo a passo quando os produtos forem aprovados

### Passo 1 — Re-gerar token OAuth

```bash
cd "/home/andre/.claude/my projects/traffic-manager"
source backend/.venv/bin/activate
python scripts/generate_linkedin_token.py
```

**Antes de rodar**, atualizar o script (linha 25) para incluir novos scopes:

```python
# De:
SCOPES = "r_ads,r_ads_reporting,rw_ads,r_organization_social"

# Para:
SCOPES = "r_ads,rw_ads,w_member_social,r_organization_social"
```

> Nota: `r_ads_reporting` foi removido (scope invalido). `w_member_social` adicionado (Share on LinkedIn).

Apos o OAuth:
1. Copiar o novo access_token
2. Copiar o novo refresh_token (se houver)
3. Atualizar em `backend/.env.development`

### Passo 2 — Testar se w_member_social permite criar posts como organizacao

```bash
python3 -c "
import httpx
TOKEN = 'NOVO_TOKEN_AQUI'
headers = {
    'Authorization': f'Bearer {TOKEN}',
    'LinkedIn-Version': '202604',
    'X-Restli-Protocol-Version': '2.0.0',
    'Content-Type': 'application/json',
}
client = httpx.Client(base_url='https://api.linkedin.com/rest', headers=headers, timeout=30)

# Testar criacao de post como organizacao
post_data = {
    'author': 'urn:li:organization:101458949',
    'lifecycleState': 'PUBLISHED',
    'visibility': 'PUBLIC',
    'distribution': {'feedDistribution': 'NONE'},
    'commentary': 'Teste — dark post para ad creative',
    'content': {
        'media': {
            'id': 'urn:li:image:D4D10AQFMF5j7T-p6ug',
            'altText': 'Teste',
        }
    },
    'adContext': {
        'dscAdAccount': 'urn:li:sponsoredAccount:520407577',
        'dscStatus': 'ACTIVE',
        'isDsc': True,
    },
}
r = client.post('/posts', json=post_data)
print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')
if r.status_code in (200, 201):
    print(f'Post URN: {r.headers.get(\"X-LinkedIn-Id\")}')
"
```

**Se funcionar (201)** → Seguir para Passo 3
**Se der 403** → Precisa do segundo app com Community Management API (ver Blocker 2)

### Passo 3 — Criar os 3 dark posts + ad creatives

Rodar o script pronto:

```bash
python3 /mnt/d/Downloads_hd/create_linkedin_campaigns.py
```

Esse script ja:
- Verifica conexao e scopes
- Pula upload de imagens (ja uploaded)
- Cria 3 dark posts como organizacao
- Cria 3 ad creatives referenciando os posts
- Vincula ao campaign 671701263

### Passo 4 — Refinar targeting no Campaign Manager

A campanha tem targeting basico. Adicionar via Campaign Manager UI:

**Adicionar industries:**
- Logistics & Supply Chain
- Legal Services
- Medical Practice
- Retail
- IT Services
- Financial Services
- Manufacturing

**Adicionar company size:**
- 11-50
- 51-200
- 201-500

**Adicionar job titles (opcional, alem de seniority):**
- CEO, CTO, COO
- Diretor de TI, Diretor de Operacoes
- Gerente de Tecnologia, Head de TI
- Socio-Diretor

**Exclusao:**
- Empresas de tecnologia/software (concorrentes)

### Passo 5 — Criar Lead Gen Form (no Campaign Manager)

1. Ir em Assets → Lead Gen Forms → Create
2. Campos:
   - Nome completo (auto-preenchido)
   - Email corporativo (auto-preenchido)
   - Telefone (obrigatorio)
   - Nome da empresa (auto-preenchido)
   - Cargo (auto-preenchido)
   - Pergunta customizada: "Qual o maior gargalo da sua operacao hoje?"
     - Processos manuais que consomem tempo
     - Sistemas que nao conversam entre si
     - Falta de visibilidade sobre a operacao
     - Quero explorar o que IA pode fazer por nos
3. Privacy Policy URL: https://axisbrasil.ai/privacidade
4. Thank you message: "Obrigado! Um especialista da Axis Brasil vai entrar em contato nos proximos minutos."
5. Vincular o form a campanha 671701263

### Passo 6 — Ativar campanha

1. Verificar que billing esta OK (cartao adicionado)
2. Verificar que todos os 3 ads estao criados
3. Verificar targeting
4. Mudar campaign status de PAUSED → ACTIVE
5. **NAO MEXER por 2 semanas** (learning phase)

---

## Conteudo dos 3 anuncios

### Anuncio 1: Case COMEX

| Campo | Conteudo |
|-------|----------|
| Imagem | `axis_criativo_07_linkedin_comex.png` (1200x628) |
| Intro text | 4 horas por operacao → 15 minutos. Reducao de 94% no tempo de processamento em COMEX com software sob medida e IA nativa. Diagnostico gratuito. |
| Headline | Sua operacao ainda depende de processos manuais? Isso tem solucao. |
| Description | Engenharia de software com IA integrada. Resultados em semanas. |
| URL | https://axisbrasil.ai/diagnostico-ia |
| CTA | Learn More |

### Anuncio 2: Dor do CTO

| Campo | Conteudo |
|-------|----------|
| Imagem | `axis_criativo_08_linkedin_cto.png` (1200x628) |
| Intro text | O seu time de TI gasta 80% do tempo mantendo sistemas legados. Sobra 20% para inovacao. A Axis e a extensao tecnica que voce precisa. |
| Headline | Equipe sobrecarregada? Nos construimos o que voces nao tem tempo. |
| Description | Engenharia de software sob medida. Stack agnostico. IA nativa. |
| URL | https://axisbrasil.ai/diagnostico-ia |
| CTA | Learn More |

### Anuncio 3: Estatistica

| Campo | Conteudo |
|-------|----------|
| Imagem | `axis_criativo_09_linkedin_estatistica.png` (1200x628) |
| Intro text | 94,5% das empresas de software no Brasil sao micro ou pequenas. A maioria nao aguenta um projeto de verdade. Nos aguentamos. |
| Headline | Nao somos consultoria de IA. Somos engenheiros de software com IA nativa. |
| Description | Ecossistemas digitais completos. Resultados em semanas. |
| URL | https://axisbrasil.ai/diagnostico-ia |
| CTA | Learn More |

---

## Credenciais e referencias

| Item | Valor |
|------|-------|
| Ad Account ID | 520407577 |
| Organization URN | urn:li:organization:101458949 |
| Client ID | 77ak6swkvyytru |
| Campaign Group ID | 924507643 |
| Campaign ID | 671701263 |
| Token scopes atuais | r_ads, rw_ads |
| Token expira | ~June 2026 (60 dias) |
| Refresh token | Sim (365 dias) |
| Script OAuth | `scripts/generate_linkedin_token.py` |
| Script criacao | `/mnt/d/Downloads_hd/create_linkedin_campaigns.py` |
| Plano de campanha | `/mnt/d/Downloads_hd/AXIS_PLANO_ADS_V2.md` |

---

## Apos lancamento (checklist semanal)

- [ ] Revisar CPL vs meta (<$20 / ~R$120)
- [ ] Revisar CTR (meta >0.4%)
- [ ] Verificar frequencia (<3.0)
- [ ] Coletar feedback do SDR sobre qualidade dos leads
- [ ] NAO editar campanha nas primeiras 2 semanas
- [ ] Se CPL > 3x meta por 5+ dias → pausar e revisar
- [ ] Se CTR < 0.2% apos 1000+ impressoes → pausar criativo
