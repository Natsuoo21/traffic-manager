"""
Diagnóstico completo do Lead Form e criativos Meta Ads.

Verifica:
  1. Se o lead form ID 1019246187948292 existe e está funcional
  2. Lista todos os lead forms da Page
  3. Verifica como cada ad referencia (ou não) o lead form
  4. Mostra CTA, link e creative de cada ad ativo
  5. Verifica status do pixel e eventos recentes

Usage:
    cd /home/andre/.claude/my\ projects/traffic-manager
    python scripts/diagnose_meta_leadform.py
"""

import json
import sys
from datetime import datetime, timedelta

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GRAPH_URL = "https://graph.facebook.com/v21.0"
LEAD_FORM_ID = "1019246187948292"
AD_ACCOUNT_ID = "act_655316296315238"
PAGE_ID = "1013933218479589"
PIXEL_ID = "980253308330567"
TOPO_CAMPAIGN_ID = "120242399493880148"
REMARKETING_CAMPAIGN_ID = "120242399793820148"


def load_token() -> str:
    try:
        from dotenv import dotenv_values
        env = dotenv_values("backend/.env.development")
        token = env.get("META_ACCESS_TOKEN", "")
    except ImportError:
        token = ""
    if not token:
        print("ERROR: META_ACCESS_TOKEN not found in backend/.env.development")
        sys.exit(1)
    return token


def api_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET request to Graph API. Returns JSON or error dict."""
    p = {"access_token": token}
    if params:
        p.update(params)
    try:
        resp = httpx.get(f"{GRAPH_URL}/{path}", params=p, timeout=30)
        data = resp.json()
        if "error" in data:
            return {"_error": True, **data["error"]}
        return data
    except Exception as e:
        return {"_error": True, "message": str(e)}


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# 1. Check specific lead form
# ---------------------------------------------------------------------------

def check_lead_form(token: str) -> dict | None:
    section("1. LEAD FORM — ID " + LEAD_FORM_ID)

    fields = "id,name,status,locale,created_time,page_id,question_page_custom_headline,questions,privacy_policy_url,follow_up_action_url"
    data = api_get(LEAD_FORM_ID, token, {"fields": fields})

    if data.get("_error"):
        print(f"  ERRO ao acessar lead form: {data.get('message', '?')}")
        print(f"  Code: {data.get('code', '?')}, Subcode: {data.get('error_subcode', '?')}")
        print()
        print("  Possíveis causas:")
        print("  - Form foi deletado")
        print("  - Token não tem permissão 'leads_retrieval' ou 'pages_manage_ads'")
        print("  - Form pertence a outra Page")
        print()
        print("  AÇÃO: Verificar manualmente no Gerenciador de Anúncios > Assets > Lead Gen Forms")
        return None

    print(f"  Nome:    {data.get('name', '?')}")
    print(f"  Status:  {data.get('status', '?')}")
    print(f"  Locale:  {data.get('locale', '?')}")
    print(f"  Page ID: {data.get('page_id', '?')}")
    print(f"  Criado:  {data.get('created_time', '?')}")
    print(f"  Privacy: {data.get('privacy_policy_url', '?')}")
    print(f"  Follow-up URL: {data.get('follow_up_action_url', '?')}")

    questions = data.get("questions", {}).get("data", [])
    if questions:
        print(f"\n  Perguntas ({len(questions)}):")
        for q in questions:
            print(f"    - {q.get('label', q.get('key', '?'))} [{q.get('type', '?')}]")

    return data


# ---------------------------------------------------------------------------
# 2. List all lead forms on the Page
# ---------------------------------------------------------------------------

def list_page_lead_forms(token: str) -> list:
    section("2. TODOS OS LEAD FORMS DA PAGE " + PAGE_ID)

    data = api_get(f"{PAGE_ID}/leadgen_forms", token, {
        "fields": "id,name,status,created_time,leads_count",
        "limit": "50",
    })

    if data.get("_error"):
        print(f"  ERRO ao listar forms da Page: {data.get('message', '?')}")
        print(f"  Code: {data.get('code', '?')}")
        print()
        print("  Possíveis causas:")
        print("  - Token sem permissão 'pages_show_list' ou 'pages_manage_ads'")
        print("  - Page ID incorreto")
        return []

    forms = data.get("data", [])
    if not forms:
        print("  Nenhum lead form encontrado na Page.")
        print("  AÇÃO: Criar um novo lead form no Gerenciador de Anúncios")
        return []

    print(f"  Encontrados {len(forms)} lead form(s):\n")
    for f in forms:
        print(f"  [{f.get('id')}]")
        print(f"    Nome:   {f.get('name', '?')}")
        print(f"    Status: {f.get('status', '?')}")
        print(f"    Leads:  {f.get('leads_count', '?')}")
        print(f"    Criado: {f.get('created_time', '?')}")
        print()

    return forms


# ---------------------------------------------------------------------------
# 3. Check ads and their creatives (CTA, link, lead form ref)
# ---------------------------------------------------------------------------

def check_campaign_ads(token: str, campaign_id: str, campaign_name: str) -> None:
    section(f"3. ADS DA CAMPANHA: {campaign_name}")

    # Get ad sets
    ad_sets_data = api_get(f"{campaign_id}/adsets", token, {
        "fields": "id,name,status",
    })
    if ad_sets_data.get("_error"):
        print(f"  ERRO ao buscar ad sets: {ad_sets_data.get('message', '?')}")
        return

    ad_sets = ad_sets_data.get("data", [])
    print(f"  Ad Sets: {len(ad_sets)}\n")

    for ad_set in ad_sets:
        print(f"  --- Ad Set: {ad_set['name']} [{ad_set['status']}] ---")

        # Get ads
        ads_data = api_get(f"{ad_set['id']}/ads", token, {
            "fields": "id,name,status,creative{id,name,title,body,call_to_action_type,object_story_spec,asset_feed_spec,link_url,effective_object_story_id}",
        })
        if ads_data.get("_error"):
            print(f"    ERRO ao buscar ads: {ads_data.get('message', '?')}")
            continue

        ads = ads_data.get("data", [])
        for ad in ads:
            print(f"\n    Ad: {ad['name']} [{ad['status']}] (ID: {ad['id']})")

            creative = ad.get("creative", {})
            if not creative:
                print("      Creative: NENHUM")
                continue

            creative_id = creative.get("id", "?")
            print(f"      Creative ID: {creative_id}")

            # Fetch full creative details
            creative_data = api_get(creative_id, token, {
                "fields": "id,name,title,body,call_to_action_type,object_story_spec,link_url,effective_object_story_id,asset_feed_spec",
            })

            if creative_data.get("_error"):
                print(f"      ERRO ao buscar creative: {creative_data.get('message', '?')}")
                continue

            cta = creative_data.get("call_to_action_type", "N/A")
            link_url = creative_data.get("link_url", "N/A")
            print(f"      CTA Type:  {cta}")
            print(f"      Link URL:  {link_url}")

            # Check object_story_spec for lead form reference
            oss = creative_data.get("object_story_spec", {})
            if oss:
                # Lead form can be in link_data.call_to_action.value.lead_gen_form_id
                link_data = oss.get("link_data", {})
                if link_data:
                    ld_link = link_data.get("link", "N/A")
                    ld_cta = link_data.get("call_to_action", {})
                    ld_cta_type = ld_cta.get("type", "N/A")
                    ld_cta_value = ld_cta.get("value", {})
                    lead_form_ref = ld_cta_value.get("lead_gen_form_id", "NENHUM")

                    print(f"      Story Link:      {ld_link}")
                    print(f"      Story CTA Type:  {ld_cta_type}")
                    print(f"      Lead Form Ref:   {lead_form_ref}")

                    if lead_form_ref == "NENHUM":
                        print("      ⚠ PROBLEMA: Ad NÃO referencia lead form nativo!")
                        print("        → Cliques vão para URL externa em vez de abrir formulário")
                    elif lead_form_ref == LEAD_FORM_ID:
                        print("      ✓ Lead form correto vinculado")
                    else:
                        print(f"      ⚠ Lead form diferente do esperado ({LEAD_FORM_ID})")
                else:
                    print("      object_story_spec sem link_data")
                    # Check video_data
                    video_data = oss.get("video_data", {})
                    if video_data:
                        vd_cta = video_data.get("call_to_action", {})
                        vd_cta_value = vd_cta.get("value", {})
                        lead_form_ref = vd_cta_value.get("lead_gen_form_id", "NENHUM")
                        print(f"      Video CTA Type:  {vd_cta.get('type', 'N/A')}")
                        print(f"      Lead Form Ref:   {lead_form_ref}")
            else:
                print("      object_story_spec: VAZIO")

            # Check asset_feed_spec (for dynamic creative)
            afs = creative_data.get("asset_feed_spec", {})
            if afs:
                print("      [Dynamic Creative / Asset Feed]")
                ctas_list = afs.get("call_to_action_types", [])
                if ctas_list:
                    print(f"      Asset CTAs: {ctas_list}")
                bodies = afs.get("bodies", [])
                links = afs.get("link_urls", [])
                if links:
                    for lu in links:
                        print(f"      Asset Link: {lu.get('website_url', '?')}")

        print()


# ---------------------------------------------------------------------------
# 4. Check pixel status and recent events
# ---------------------------------------------------------------------------

def check_pixel(token: str) -> None:
    section("4. PIXEL — ID " + PIXEL_ID)

    # Pixel info
    data = api_get(PIXEL_ID, token, {
        "fields": "id,name,last_fired_time,owner_ad_account",
    })

    if data.get("_error"):
        print(f"  ERRO ao acessar pixel: {data.get('message', '?')}")
        return

    print(f"  Nome:           {data.get('name', '?')}")
    print(f"  Last Fired:     {data.get('last_fired_time', '?')}")
    print(f"  Owner Account:  {data.get('owner_ad_account', {}).get('id', '?')}")

    # Event stats (last 7 days)
    print("\n  Eventos recentes (últimos 7 dias):")
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    stats = api_get(f"{PIXEL_ID}/stats", token, {
        "start_time": week_ago,
        "end_time": today,
    })

    if stats.get("_error"):
        print(f"    ERRO ao buscar stats do pixel: {stats.get('message', '?')}")
        print(f"    Code: {stats.get('code', '?')}")
        # Try alternate: da_checks
        print("\n  Tentando diagnostic (da_checks)...")
        da = api_get(f"{PIXEL_ID}/da_checks", token)
        if not da.get("_error"):
            checks = da.get("data", [])
            for c in checks:
                print(f"    {c.get('name', '?')}: {c.get('result', '?')}")
    else:
        events = stats.get("data", [])
        if not events:
            print("    Nenhum dado de eventos retornado.")
        for ev in events:
            print(f"    {ev.get('event', '?')}: {ev.get('count', 0)} disparos")


# ---------------------------------------------------------------------------
# 5. Check ad account spend and status
# ---------------------------------------------------------------------------

def check_account(token: str) -> None:
    section("5. CONTA — " + AD_ACCOUNT_ID)

    data = api_get(AD_ACCOUNT_ID, token, {
        "fields": "name,account_status,amount_spent,balance,currency,spend_cap,funding_source_details",
    })

    if data.get("_error"):
        print(f"  ERRO: {data.get('message', '?')}")
        return

    status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "CLOSED"}
    acct_status = data.get("account_status", "?")

    print(f"  Nome:       {data.get('name', '?')}")
    print(f"  Status:     {status_map.get(acct_status, acct_status)}")
    print(f"  Gasto total: R${int(data.get('amount_spent', 0)) / 100:.2f}")
    print(f"  Balance:    R${int(data.get('balance', 0)) / 100:.2f}")
    print(f"  Spend Cap:  R${int(data.get('spend_cap', 0)) / 100:.2f}")
    print(f"  Moeda:      {data.get('currency', '?')}")


# ---------------------------------------------------------------------------
# 6. Token permission check
# ---------------------------------------------------------------------------

def check_permissions(token: str) -> None:
    section("6. PERMISSÕES DO TOKEN")

    data = api_get("me/permissions", token)
    if data.get("_error"):
        print(f"  ERRO: {data.get('message', '?')}")
        return

    perms = data.get("data", [])
    needed = [
        "ads_management", "ads_read", "pages_show_list",
        "pages_manage_ads", "leads_retrieval", "pages_read_engagement",
    ]

    print(f"  Total permissões: {len(perms)}\n")
    for p in sorted(perms, key=lambda x: x.get("permission", "")):
        perm_name = p.get("permission", "?")
        status = p.get("status", "?")
        marker = "✓" if status == "granted" else "✗"
        flag = " ← NECESSÁRIO" if perm_name in needed else ""
        print(f"    {marker} {perm_name}: {status}{flag}")

    print("\n  Permissões requeridas para lead forms:")
    for n in needed:
        found = any(p.get("permission") == n and p.get("status") == "granted" for p in perms)
        print(f"    {'✓' if found else '✗ FALTA'} {n}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("  META ADS — DIAGNÓSTICO DE LEAD FORMS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    token = load_token()
    print(f"\n  Token: ...{token[-20:]}")

    # Run all checks
    check_permissions(token)
    check_account(token)
    form = check_lead_form(token)
    list_page_lead_forms(token)
    check_campaign_ads(token, TOPO_CAMPAIGN_ID, "Topo de Funil")
    check_campaign_ads(token, REMARKETING_CAMPAIGN_ID, "Remarketing")
    check_pixel(token)

    # Summary
    section("RESUMO E AÇÕES RECOMENDADAS")
    print("  1. Se o lead form não existe → criar um novo no Gerenciador de Anúncios")
    print("  2. Se existe mas não está vinculado nos ads → atualizar criativos")
    print("  3. Se o token não tem 'leads_retrieval' → regerar token com essa permissão")
    print("  4. Adicionar fbq('track', 'Lead') no site para remarketing funcionar")
    print("  5. Adicionar saldo na conta Meta (verificar balance acima)")
    print()


if __name__ == "__main__":
    main()
