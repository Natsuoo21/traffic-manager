"""
Automacao pos-token: diagnostico + vinculacao de lead form nos ads.

Fluxo:
  1. Recebe token curto do Graph API Explorer
  2. Troca por long-lived (60 dias)
  3. Atualiza backend/.env.development automaticamente
  4. Verifica permissoes (pages_manage_ads, leads_retrieval)
  5. Lista lead forms da Page
  6. Se form existir -> vincula nos 6 ads
  7. Se nao existir -> instrui a criar um novo

Usage:
    cd /home/andre/.claude/my\ projects/traffic-manager
    python scripts/setup_meta_leadform.py <SHORT_LIVED_TOKEN>

    # Ou com token ja long-lived (pula a troca):
    python scripts/setup_meta_leadform.py <TOKEN> --skip-exchange
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GRAPH_URL = "https://graph.facebook.com/v21.0"
AD_ACCOUNT_ID = "act_655316296315238"
PAGE_ID = "1013933218479589"
LEAD_FORM_ID = "1019246187948292"  # form original (verificar se existe)

# IDs dos 6 ads que precisam de lead form
ADS_TO_FIX = {
    # Topo de Funil
    "120242399791620148": "Ad 2 - Dor Operacional",
    "120242399790680148": "Ad 1 - Case COMEX",
    "120242399792310148": "Ad 3 - Provocacao IA",
    "120242399793420148": "Ad 4 - Pergunta Direta",
    # Remarketing
    "120242399809930148": "Remarketing Ad 2 - Diagnostico",
    "120242399809290148": "Remarketing Ad 1 - Case Juridico",
}

ENV_FILE = Path(__file__).parent.parent / "backend" / ".env.development"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api_get(path: str, token: str, params: dict | None = None) -> dict:
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


def api_post(path: str, token: str, data: dict | None = None) -> dict:
    try:
        payload = {"access_token": token}
        if data:
            payload.update(data)
        resp = httpx.post(f"{GRAPH_URL}/{path}", data=payload, timeout=30)
        result = resp.json()
        if "error" in result:
            return {"_error": True, **result["error"]}
        return result
    except Exception as e:
        return {"_error": True, "message": str(e)}


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def fail(msg: str) -> None:
    print(f"  [FALHA] {msg}")


def info(msg: str) -> None:
    print(f"  [INFO] {msg}")


# ---------------------------------------------------------------------------
# Step 1: Exchange token
# ---------------------------------------------------------------------------


def exchange_token(short_token: str) -> str:
    """Troca token curto por long-lived (60 dias)."""
    section("STEP 1: TROCAR TOKEN POR LONG-LIVED")

    try:
        from dotenv import dotenv_values
        env = dotenv_values(str(ENV_FILE))
        app_id = env.get("META_APP_ID", "")
        app_secret = env.get("META_APP_SECRET", "")
    except ImportError:
        fail("python-dotenv nao instalado. Instale: pip install python-dotenv")
        sys.exit(1)

    if not app_id or not app_secret:
        fail("META_APP_ID ou META_APP_SECRET nao encontrado em .env.development")
        sys.exit(1)

    resp = httpx.get(
        f"{GRAPH_URL}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )

    if resp.status_code != 200:
        fail(f"Erro ao trocar token: {resp.text}")
        sys.exit(1)

    data = resp.json()
    long_token = data["access_token"]
    expires_in = data.get("expires_in", "?")

    ok(f"Token long-lived obtido (expira em {expires_in}s / ~60 dias)")
    print(f"  Token: ...{long_token[-20:]}")

    return long_token


# ---------------------------------------------------------------------------
# Step 2: Update .env.development
# ---------------------------------------------------------------------------


def update_env_file(new_token: str) -> None:
    """Atualiza META_ACCESS_TOKEN no .env.development."""
    section("STEP 2: ATUALIZAR .env.development")

    content = ENV_FILE.read_text()
    old_match = re.search(r"^META_ACCESS_TOKEN=(.*)$", content, re.MULTILINE)

    if not old_match:
        fail("META_ACCESS_TOKEN nao encontrado no .env.development")
        return

    old_token = old_match.group(1)
    if old_token == new_token:
        info("Token ja esta atualizado (mesmo valor)")
        return

    new_content = content.replace(
        f"META_ACCESS_TOKEN={old_token}",
        f"META_ACCESS_TOKEN={new_token}",
    )
    ENV_FILE.write_text(new_content)
    ok(f"Token atualizado em {ENV_FILE}")
    info(f"Antigo: ...{old_token[-20:]}")
    info(f"Novo:   ...{new_token[-20:]}")


# ---------------------------------------------------------------------------
# Step 3: Check permissions
# ---------------------------------------------------------------------------


def check_permissions(token: str) -> bool:
    """Verifica se o token tem as permissoes necessarias. Retorna True se ok."""
    section("STEP 3: VERIFICAR PERMISSOES")

    data = api_get("me/permissions", token)
    if data.get("_error"):
        fail(f"Erro ao verificar permissoes: {data.get('message', '?')}")
        return False

    perms = data.get("data", [])
    granted = {p["permission"] for p in perms if p.get("status") == "granted"}

    required = {
        "ads_management": "Gerenciar campanhas e ads",
        "ads_read": "Ler metricas",
        "pages_manage_ads": "Criar/listar lead forms, vincular aos ads",
        "leads_retrieval": "Ler leads submetidos",
        "pages_read_engagement": "Dependencia do leads_retrieval",
        "pages_show_list": "Listar Pages gerenciadas",
    }

    all_ok = True
    for perm, desc in required.items():
        if perm in granted:
            ok(f"{perm} — {desc}")
        else:
            fail(f"{perm} — {desc}")
            all_ok = False

    if not all_ok:
        print()
        fail("Token nao tem todas as permissoes necessarias.")
        print("  Volte ao Graph API Explorer e adicione as permissoes faltantes.")
        print("  URL: https://developers.facebook.com/tools/explorer/")

    return all_ok


# ---------------------------------------------------------------------------
# Step 4: Find lead form
# ---------------------------------------------------------------------------


def find_lead_form(token: str) -> str | None:
    """Tenta acessar o form conhecido ou lista todos da Page. Retorna form_id."""
    section("STEP 4: LOCALIZAR LEAD FORM")

    # 4a. Tentar o form ID conhecido
    info(f"Verificando form ID {LEAD_FORM_ID}...")
    data = api_get(LEAD_FORM_ID, token, {
        "fields": "id,name,status,locale,created_time,questions",
    })

    if not data.get("_error"):
        ok(f"Form encontrado: {data.get('name', '?')} [{data.get('status', '?')}]")
        print(f"  ID: {data['id']}")
        print(f"  Locale: {data.get('locale', '?')}")
        print(f"  Criado: {data.get('created_time', '?')}")
        questions = data.get("questions", {}).get("data", [])
        if questions:
            print(f"  Perguntas ({len(questions)}):")
            for q in questions:
                print(f"    - {q.get('label', q.get('key', '?'))} [{q.get('type', '?')}]")
        return data["id"]

    info(f"Form {LEAD_FORM_ID} nao acessivel: {data.get('message', '?')}")

    # 4b. Listar todos os forms da Page
    info(f"Listando todos os lead forms da Page {PAGE_ID}...")
    page_forms = api_get(f"{PAGE_ID}/leadgen_forms", token, {
        "fields": "id,name,status,created_time,leads_count",
        "limit": "50",
    })

    if page_forms.get("_error"):
        fail(f"Erro ao listar forms: {page_forms.get('message', '?')}")
        return None

    forms = page_forms.get("data", [])
    if not forms:
        fail("Nenhum lead form encontrado na Page.")
        print()
        print("  ACAO NECESSARIA:")
        print("  1. Abra o Gerenciador de Anuncios do Meta")
        print("  2. Va em Ferramentas > Formularios Instantaneos")
        print("  3. Crie um novo formulario com os campos desejados")
        print("  4. Anote o ID do formulario criado")
        print("  5. Rode este script novamente (ele vai encontrar o form)")
        return None

    print(f"\n  Encontrados {len(forms)} form(s):\n")
    for i, f in enumerate(forms):
        status = f.get("status", "?")
        leads = f.get("leads_count", 0)
        print(f"  [{i+1}] {f['id']} — {f.get('name', '?')} [{status}] ({leads} leads)")

    # Usar o primeiro form ativo, ou o primeiro da lista
    active_forms = [f for f in forms if f.get("status") == "ACTIVE"]
    chosen = active_forms[0] if active_forms else forms[0]

    ok(f"Usando form: {chosen['id']} — {chosen.get('name', '?')}")
    return chosen["id"]


# ---------------------------------------------------------------------------
# Step 5: Link lead form to ads
# ---------------------------------------------------------------------------


def get_ad_creative_details(ad_id: str, token: str) -> dict | None:
    """Busca os detalhes do creative atual de um ad."""
    ad_data = api_get(ad_id, token, {
        "fields": "id,name,creative{id,object_story_spec}",
    })
    if ad_data.get("_error"):
        return None
    return ad_data


def link_form_to_ads(token: str, form_id: str) -> None:
    """Vincula o lead form nos 6 ads atualizando o creative."""
    section("STEP 5: VINCULAR LEAD FORM NOS ADS")

    info(f"Lead Form ID: {form_id}")
    print(f"  Ads para atualizar: {len(ADS_TO_FIX)}\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for ad_id, ad_name in ADS_TO_FIX.items():
        print(f"  --- {ad_name} (ID: {ad_id}) ---")

        # 1. Buscar creative atual
        ad_data = get_ad_creative_details(ad_id, token)
        if not ad_data:
            fail(f"Nao consegui ler o ad {ad_id}")
            fail_count += 1
            continue

        creative = ad_data.get("creative", {})
        creative_id = creative.get("id")
        if not creative_id:
            fail("Ad sem creative")
            fail_count += 1
            continue

        oss = creative.get("object_story_spec", {})
        link_data = oss.get("link_data", {})

        # 2. Verificar se ja tem lead form vinculado
        existing_cta = link_data.get("call_to_action", {})
        existing_form = existing_cta.get("value", {}).get("lead_gen_form_id")

        if existing_form == form_id:
            info(f"Ja vinculado ao form correto")
            skip_count += 1
            continue

        if existing_form:
            info(f"Form diferente vinculado: {existing_form} — sera substituido")

        # 3. Criar novo creative com lead form
        # Reconstruir o object_story_spec com o lead_gen_form_id
        new_link_data = dict(link_data)
        new_link_data["call_to_action"] = {
            "type": "SIGN_UP",
            "value": {
                "lead_gen_form_id": form_id,
            },
        }

        new_oss = dict(oss)
        new_oss["link_data"] = new_link_data

        # Criar novo creative
        create_result = api_post(f"{AD_ACCOUNT_ID}/adcreatives", token, {
            "object_story_spec": json.dumps(new_oss),
        })

        if create_result.get("_error"):
            fail(f"Erro ao criar creative: {create_result.get('message', '?')}")
            print(f"    Code: {create_result.get('code', '?')}")
            fail_count += 1
            continue

        new_creative_id = create_result.get("id")
        if not new_creative_id:
            fail("Creative criado mas sem ID retornado")
            fail_count += 1
            continue

        info(f"Novo creative criado: {new_creative_id}")

        # 4. Atualizar o ad para usar o novo creative
        update_result = api_post(ad_id, token, {
            "creative": json.dumps({"creative_id": new_creative_id}),
        })

        if update_result.get("_error"):
            fail(f"Erro ao atualizar ad: {update_result.get('message', '?')}")
            fail_count += 1
            continue

        ok(f"Lead form vinculado com sucesso!")
        success_count += 1
        print()

    # Resumo
    print(f"\n  --- RESUMO ---")
    print(f"  Sucesso:   {success_count}/{len(ADS_TO_FIX)}")
    print(f"  Ja ok:     {skip_count}/{len(ADS_TO_FIX)}")
    print(f"  Falha:     {fail_count}/{len(ADS_TO_FIX)}")


# ---------------------------------------------------------------------------
# Step 6: Verify
# ---------------------------------------------------------------------------


def verify_ads(token: str, form_id: str) -> None:
    """Verifica se os ads agora referenciam o lead form."""
    section("STEP 6: VERIFICACAO FINAL")

    all_good = True
    for ad_id, ad_name in ADS_TO_FIX.items():
        ad_data = get_ad_creative_details(ad_id, token)
        if not ad_data:
            fail(f"{ad_name}: nao consegui ler")
            all_good = False
            continue

        creative = ad_data.get("creative", {})
        oss = creative.get("object_story_spec", {})
        link_data = oss.get("link_data", {})
        cta_value = link_data.get("call_to_action", {}).get("value", {})
        linked_form = cta_value.get("lead_gen_form_id", "NENHUM")

        if linked_form == form_id:
            ok(f"{ad_name}: form vinculado corretamente")
        else:
            fail(f"{ad_name}: form = {linked_form} (esperado {form_id})")
            all_good = False

    if all_good:
        print("\n  TODOS OS ADS ESTAO COM LEAD FORM VINCULADO!")
        print("  Os leads agora serao capturados diretamente no Meta.")
    else:
        print("\n  Alguns ads ainda precisam de atencao. Verifique os erros acima.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 70)
    print("  META ADS — SETUP AUTOMATICO DE LEAD FORM")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Parse args
    skip_exchange = "--skip-exchange" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("\nUsage:")
        print("  python scripts/setup_meta_leadform.py <TOKEN>")
        print("  python scripts/setup_meta_leadform.py <TOKEN> --skip-exchange")
        print()
        print("  <TOKEN> = token do Graph API Explorer")
        print("  --skip-exchange = pula a troca por long-lived (se ja tiver)")
        sys.exit(1)

    input_token = args[0]

    # Step 1: Exchange token (optional)
    if skip_exchange:
        info("Pulando troca de token (--skip-exchange)")
        token = input_token
    else:
        token = exchange_token(input_token)

    # Step 2: Update .env
    update_env_file(token)

    # Step 3: Check permissions
    perms_ok = check_permissions(token)
    if not perms_ok:
        print("\n  Abortando — corrija as permissoes e rode novamente.")
        sys.exit(1)

    # Step 4: Find lead form
    form_id = find_lead_form(token)
    if not form_id:
        print("\n  Abortando — crie um lead form e rode novamente.")
        sys.exit(1)

    # Step 5: Link form to ads
    link_form_to_ads(token, form_id)

    # Step 6: Verify
    verify_ads(token, form_id)

    # Done
    section("CONCLUIDO")
    print("  Proximo passo: verificar no Gerenciador de Anuncios se os ads")
    print("  agora mostram o formulario instantaneo ao clicar no CTA.")
    print()
    print("  Para ler os leads capturados:")
    print(f"    GET /{form_id}/leads?access_token=<TOKEN>")
    print()


if __name__ == "__main__":
    main()
