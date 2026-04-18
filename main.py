import streamlit as st
import pandas as pd
import math
import requests
from datetime import datetime, timezone, timedelta
from fpdf import FPDF
from supabase import create_client, Client
import io

# --- 0. CONSTANTES GLOBAIS ---
LINKS_MERCADO_PAGO = {
    "mensal": "https://mpago.la/1GddQRG",
    "trimestral": "https://mpago.la/224N4Zw",
    "anual": "https://mpago.la/2B9zSZz"
}

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="VoltSpec Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="application-name" content="VoltSpec Pro">
    <meta name="apple-mobile-web-app-title" content="VoltSpec Pro">
    <meta name="theme-color" content="#000000">
    <meta name="msapplication-navbutton-color" content="#000000">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM BANCO (SUPABASE) ---
URL_SUPA = st.secrets.get("SUPABASE_URL", "")
KEY_SUPA = st.secrets.get("SUPABASE_KEY", "")
MP_ACCESS_TOKEN = st.secrets.get("MP_ACCESS_TOKEN", "") # Adicione isso no seu secrets.toml

@st.cache_resource
def init_connection():
    try:
        return create_client(URL_SUPA, KEY_SUPA)
    except Exception as e:
        st.error(f"❌ Erro na conexão com o Supabase: {e}")
        return None

supabase = init_connection()

if supabase is None:
    st.warning("⚠️ Aplicativo sem conexão com o banco de dados. Algumas funções estarão indisponíveis.")

def get_supabase_autenticado():
    global supabase
    if supabase is None:
        return None
    try:
        session = st.session_state.get('session')
        if session and hasattr(session, 'access_token') and session.access_token:
            supabase.auth.set_session(session.access_token, session.refresh_token)
        return supabase
    except Exception as e:
        st.warning(f"⚠️ Erro ao autenticar sessão: {e}")
        return supabase

# --- 3. NOVA FUNÇÃO: VERIFICAR MERCADO PAGO ---
def verificar_pagamento_direto_mp(email_usuario):
    """
    Consulta o Mercado Pago e devolve (Status, Dias a libertar).
    """
    if not MP_ACCESS_TOKEN:
        return False, 0
        
    url = "https://api.mercadopago.com/v1/payments/search"
    params = {
        "payer.email": email_usuario.strip(),
        "status": "approved",
        "sort": "date_created",
        "criteria": "desc" # Pega sempre o pagamento mais recente
    }
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("results") and len(dados.get("results")) > 0:
                ultimo_pagamento = dados["results"][0]
                valor_pago = float(ultimo_pagamento.get("transaction_amount", 0))
                
                # Define os dias com base no valor do PIX/Cartão
                if valor_pago >= 149.00:   dias = 365 # Anual
                elif valor_pago >= 49.00: dias = 90  # Trimestral
                elif valor_pago >= 19.00: dias = 30  # Mensal
                elif valor_pago == 1.00:  dias = 1   # Teste Araxá
                else:                     dias = 30
                    
                return True, dias
        return False, 0
    except Exception:
        return False, 0
# --- 4. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---
def limpar_texto(txt):
    if not txt or txt is None:
        return ""
    try:
        return str(txt).encode('latin-1', 'ignore').decode('latin-1').replace("²", "2").strip()
    except Exception:
        return ""

def montar_cabecalho_pdf(pdf):
    p = st.session_state.get('perfil', {})
    
    emp      = limpar_texto(p.get('nome_empresa', '')) or 'VoltSpec Pro'
    crt      = limpar_texto(p.get('crt', ''))
    tel      = limpar_texto(p.get('telefone', ''))
    cnpj     = limpar_texto(p.get('cnpj', ''))
    cidade   = limpar_texto(p.get('endereco', ''))
    email    = limpar_texto(p.get('email_contato', ''))

    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_text_color(255, 255, 255)

    pdf.set_font("Arial", "B", 16)
    pdf.set_xy(0, 6)
    pdf.cell(210, 10, emp.upper(), align="C", ln=True)

    linha1 = ""
    if crt:  linha1 += f"Reg.: {crt}"
    if tel:  linha1 += f"  | Tel: {tel}"
    if linha1:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, linha1.strip(), align="C", ln=True)

    linha2 = ""
    if cnpj:   linha2 += f"CNPJ: {cnpj}"
    if cidade: linha2 += f"  | {cidade}"
    if linha2:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, linha2.strip(), align="C", ln=True)

    if email:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, email, align="C", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

def gerar_pdf_universal(titulo, df_dados, colunas_w, headers):
    try:
        hoje = datetime.now()
        validade = hoje + timedelta(days=7)
        hoje_str = hoje.strftime('%d/%m/%Y %H:%M')
        validade_str = validade.strftime('%d/%m/%Y')

        pdf = FPDF()
        pdf.add_page()
        montar_cabecalho_pdf(pdf)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"RELATORIO: {limpar_texto(titulo)}", "B", 1, "L")
        
        # --- ADICIONADO VALIDADE ---
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 5, f"Gerado em: {hoje_str}", 0, 1, "R")
        pdf.set_text_color(255, 0, 0)
        pdf.set_font("Arial", "BI", 8)
        pdf.cell(0, 5, f"VÁLIDO ATÉ: {validade_str}", 0, 1, "R")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 9)
        for i, h in enumerate(headers):
            pdf.cell(colunas_w[i], 8, limpar_texto(h), 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        total = 0
        for _, r in df_dados.iterrows():
            try:
                qtd = float(r.get("Qtd", 0) or 0)
                if qtd > 0:
                    preco = float(r.get("Preco", 0) or 0)
                    sub = qtd * preco
                    total += sub
                    pdf.cell(colunas_w[0], 7, limpar_texto(r["Descricao"]), 1)
                    pdf.cell(colunas_w[1], 7, str(int(qtd)), 1, 0, "C")
                    pdf.cell(colunas_w[2], 7, f"{preco:.2f}", 1, 0, "C")
                    pdf.cell(colunas_w[3], 7, f"{sub:.2f}", 1, 1, "C")
            except (ValueError, TypeError, KeyError):
                continue

        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", 0, 1, "R")
        return pdf.output(dest="S").encode("latin-1")
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

def gerar_pdf_resultado_lumino(dados, perfil):
    try:
        hoje = datetime.now()
        validade = hoje + timedelta(days=7)
        hoje_str = hoje.strftime('%d/%m/%Y')
        validade_str = validade.strftime('%d/%m/%Y')

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        
        empresa = limpar_texto(perfil.get('nome_empresa', 'VoltSpec Pro')) or 'VoltSpec Pro'
        titulo = f"{empresa} - Relatório Luminotécnico"
        pdf.cell(190, 10, titulo, ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Arial", "", 12)
        pdf.cell(190, 8, f"Responsável Técnico: {limpar_texto(perfil.get('crt', '---'))}", ln=True)
        pdf.cell(190, 8, f"Local/Cidade: {limpar_texto(perfil.get('endereco', '---'))}", ln=True)
        
        # --- ADICIONADO VALIDADE ---
        pdf.set_font("Arial", "I", 10)
        pdf.cell(190, 6, f"Data do Cálculo: {hoje_str}  |  Válido até: {validade_str}", ln=True)
        
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "Detalhes do Dimensionamento", ln=True)
        pdf.set_font("Arial", "", 12)
        
        nivel_lux = dados.get('nivel_lux', 0)
        area = dados.get('area', 0)
        qtd_lum = dados.get('qtd_luminarias', 0)
        pot_total = dados.get('potencia_total', 0)
        dist = dados.get('distribuicao', '0x0')
        
        pdf.cell(190, 10, f"- Nível de Iluminância Requerido: {nivel_lux} Lux", ln=True)
        pdf.cell(190, 10, f"- Área do Ambiente: {area:.2f} m²", ln=True)
        pdf.cell(190, 10, f"- Quantidade de Luminárias: {qtd_lum} unidades", ln=True)
        pdf.cell(190, 10, f"- Potência Total Instalada: {pot_total} W", ln=True)
        pdf.cell(190, 10, f"- Distribuição Sugerida: {dist}", ln=True)
        
        pdf.ln(20)
        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(190, 10, "Cálculo realizado seguindo os parâmetros da NBR ISO/CIE 8995-1 utilizando o Método dos Lúmens.")
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro ao gerar PDF luminotécnico: {e}")
        return None

# --- 5. FUNÇÕES DE BANCO DE DADOS ---
def carregar_perfil_supabase():
    try:
        if not st.session_state.get('user') or not hasattr(st.session_state.user, 'id'):
            st.warning("❌ Usuário não autenticado corretamente")
            return
        
        if 'perfil' not in st.session_state:
            st.session_state.perfil = {}
        
        cliente = get_supabase_autenticado()
        if cliente is None:
            st.warning("⚠️ Sem conexão com banco de dados")
            return
        
        res = cliente.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        if res.data:
            d = res.data[0]
            st.session_state.perfil['nome_empresa']  = d.get('nome_empresa', '')
            st.session_state.perfil['crt']           = d.get('crt', '')
            st.session_state.perfil['telefone']      = d.get('telefone', '')
            st.session_state.perfil['cnpj']          = d.get('cnpj', '')
            st.session_state.perfil['endereco']      = d.get('endereco_comercial', '')
            st.session_state.perfil['email_contato'] = d.get('email', '')
            st.session_state.perfil['data_cadastro']     = d.get('created_at', str(datetime.now(timezone.utc)))
            st.session_state.perfil['status_assinatura'] = d.get('status_assinatura', 'trial')
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar o perfil: {e}")

def salvar_perfil_supabase():
    try:
        if not st.session_state.get('user') or not hasattr(st.session_state.user, 'id'):
            st.error("❌ Erro: Usuário não autenticado")
            return
        
        cliente = get_supabase_autenticado()
        if cliente is None:
            st.error("❌ Sem conexão com banco de dados")
            return
        
        dados = {
            "id":                 st.session_state.user.id,
            "nome_empresa":       limpar_texto(st.session_state.perfil.get('nome_empresa', '')),
            "crt":                limpar_texto(st.session_state.perfil.get('crt', '')),
            "telefone":           limpar_texto(st.session_state.perfil.get('telefone', '')),
            "cnpj":               limpar_texto(st.session_state.perfil.get('cnpj', '')),
            "email":              st.session_state.user.email,
            "endereco_comercial": limpar_texto(st.session_state.perfil.get('endereco', ''))
        }
        cliente.table("profiles").upsert(dados).execute()
        st.success("✅ Sincronizado!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def formatar_data_iso(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()

# --- 6. ESTADO INICIAL ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'perfil_carregado' not in st.session_state:
    st.session_state.perfil_carregado = False

if 'dados_cargas' not in st.session_state:
    st.session_state.dados_cargas = pd.DataFrame([{
        "Comodo": "Sala", "Area (m2)": 0.0, "Perimetro (m)": 0.0,
        "Iluminacao (VA)": "-", "TUG (Qtd)": 0,
        "Potencia TUG (VA)": 0.0, "TUE (Watts)": 0.0
    }])

if 'lista_circuitos' not in st.session_state:
    st.session_state.lista_circuitos = []
if 'resumo_materiais' not in st.session_state:
    st.session_state.resumo_materiais = []

if 'perfil' not in st.session_state:
    st.session_state.perfil = {
        'nome_empresa': '', 'crt': '', 'telefone': '', 'cnpj': '', 'endereco': '', 'email_contato': '',
        'data_cadastro': formatar_data_iso(), 'status_assinatura': 'trial'
    }

# --- 7. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("⚡ VoltSpec Pro")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        em = st.text_input("E-mail")
        pw = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if supabase is None:
                st.error("❌ Sem conexão com o banco de dados.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
                    if res.user:
                        st.session_state.user    = res.user
                        st.session_state.session = res.session
                        st.session_state.logado  = True
                        st.session_state.perfil_carregado = False
                        st.rerun()
                except Exception as e:
                    st.error(f"Falha no login: {e}")
    with t2:
        nem = st.text_input("Novo E-mail")
        npw = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            if supabase is None:
                st.error("❌ Sem conexão com o banco de dados.")
            else:
                try:
                    supabase.auth.sign_up({"email": nem, "password": npw})
                    st.success("Sucesso! Verifique seu e-mail para confirmar a conta.")
                except Exception as e:
                    st.error(f"Erro no cadastro: {e}")
    st.stop()

# --- CARREGA PERFIL APÓS LOGIN ---
if st.session_state.logado and not st.session_state.perfil_carregado:
    carregar_perfil_supabase()
    st.session_state.perfil_carregado = True

# --- 8. SISTEMA PRINCIPAL E LÓGICA DE PAYWALL ---
def calcular_dias_uso():
    data_cad_str = st.session_state.perfil.get('data_cadastro', '')
    try:
        if data_cad_str:
            data_cad = datetime.fromisoformat(data_cad_str.replace('Z', '+00:00'))
        else:
            data_cad = datetime.now(timezone.utc)
    except:
        data_cad = datetime.now(timezone.utc)
    
    data_agora = datetime.now(timezone.utc)
    return max(0, (data_agora - data_cad).days)

dias_de_uso = calcular_dias_uso()
status_ass = st.session_state.perfil.get('status_assinatura', 'trial')
tem_acesso = (dias_de_uso <= 7) or (status_ass == 'ativo')

# --- CONFIGURAÇÃO DA BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("VoltSpec Pro ⚡")

if st.sidebar.button("🚪 Sair da Conta", key="btn_sair_logoff"):
    st.session_state.logado = False
    st.session_state.user   = None
    st.session_state.session = None
    st.session_state.perfil_carregado = False
    st.session_state.perfil = {
        'nome_empresa': '', 'crt': '', 'telefone': '', 'cnpj': '', 'endereco': '', 'email_contato': '',
        'data_cadastro': formatar_data_iso(), 'status_assinatura': 'trial'
    }
    st.rerun()

# --- WIDGET PREMIUM SEMPRE VISÍVEL NO TRIAL ---
if status_ass != 'ativo':
    st.sidebar.divider()
    dias_restantes = max(0, 7 - dias_de_uso)
    
    if dias_restantes > 0:
        st.sidebar.info(f"⏳ **Período de Teste:** Restam {dias_restantes} dias.")
    else:
        st.sidebar.error("🔒 Seu período de teste expirou!")
        
    with st.sidebar.expander("💎 Fazer Upgrade Agora", expanded=True):
        st.write("Gere relatórios ilimitados e salve seus cálculos na nuvem.")
        st.link_button("Assinar Mensal", LINKS_MERCADO_PAGO["mensal"], use_container_width=True)
        st.link_button("Assinar Trimestral", LINKS_MERCADO_PAGO["trimestral"], type="primary", use_container_width=True)
        st.link_button("Assinar Anual (Melhor Valor)", LINKS_MERCADO_PAGO["anual"], use_container_width=True)
    st.sidebar.divider()

# --- BLOQUEIO TOTAL DA TELA CENTRAL (TELA DE PAGAMENTO) ---
if not tem_acesso:
    st.error("🔒 Acesso Bloqueado")
    st.title("Assine o VoltSpec Pro")
    st.write("Seus 7 dias gratuitos chegaram ao fim. Para continuar usando o melhor sistema de dimensionamento elétrico, ative sua assinatura.")
    
    st.markdown("### 💎 Benefícios do Plano Profissional")
    st.write("- Dimensionamento NBR 5410 ilimitado")
    st.write("- Relatórios Luminotécnicos detalhados")
    st.write("- Geração de PDF com a Logo e Dados da sua Empresa")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🥉 **Plano Mensal**\n\nAcesso mês a mês.")
        st.link_button("💳 Assinar Mensal", LINKS_MERCADO_PAGO["mensal"], use_container_width=True)
    with col2:
        st.success("🥈 **Plano Trimestral**\n\nIdeal para projetos médios.")
        st.link_button("💳 Assinar Trimestral", LINKS_MERCADO_PAGO["trimestral"], type="primary", use_container_width=True)
    with col3:
        st.warning("🥇 **Plano Anual**\n\nMaior desconto do ano!")
        st.link_button("💳 Assinar Anual", LINKS_MERCADO_PAGO["anual"], use_container_width=True)
    
    st.write("---")
    
    # --- BOTÃO DE VERIFICAÇÃO DA TELA DE BLOQUEIO (CORRIGIDO) ---
    st.subheader("Já realizou o pagamento?")
    st.write("Clique no botão abaixo para verificar no sistema e liberar seu acesso.")
    if st.button("🔄 Verificar Pagamento e Liberar Acesso", type="primary", use_container_width=True, key="btn_paywall"):
        with st.spinner("Consultando Mercado Pago..."):
            pago, dias_adicionais = verificar_pagamento_direto_mp(st.session_state.user.email)
            if pago:
                try:
                    # 1. Calcula a nova data de vencimento
                    nova_data = datetime.now(timezone.utc) + timedelta(days=dias_adicionais)
                    nova_data_iso = nova_data.isoformat()
                    
                    # 2. Pega a conexão AUTENTICADA
                    cliente_auth = get_supabase_autenticado()
                    
                    # 3. Envia os dados
                    cliente_auth.table("profiles").update({
                        "status_assinatura": "ativo",
                        "data_vencimento": nova_data_iso
                    }).eq("id", st.session_state.user.id).execute()
                    
                    # 4. Atualiza a memória
                    st.session_state.perfil['status_assinatura'] = 'ativo'
                    st.session_state.perfil['data_vencimento'] = nova_data_iso
                    
                    st.success(f"✅ Pagamento confirmado! Acesso VIP liberado por {dias_adicionais} dias.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar banco: {e}")
            else:
                st.warning("Nenhum pagamento aprovado encontrado para este e-mail ainda. Aguarde alguns minutos.")
    
    st.stop() 
    
    # --- BOTÃO DE VERIFICAÇÃO PARA QUEM ACABOU DE PAGAR ---
    st.subheader("Já realizou o pagamento?")
    st.write("Clique no botão abaixo para verificar no sistema e liberar seu acesso.")
if st.button("🔄 Verificar Pagamento e Liberar Acesso", type="primary", use_container_width=True, key="btn_paywall"):
            with st.spinner("A consultar o servidor do Mercado Pago..."):
                pago, dias_adicionais = verificar_pagamento_direto_mp(st.session_state.user.email)
                
                if pago:
                    try:
                        # 1. Calcula a data exata
                        nova_data = datetime.now(timezone.utc) + timedelta(days=dias_adicionais)
                        nova_data_iso = nova_data.isoformat()
                        
                        # 2. Mostra o que vai ser gravado (Apenas para teste)
                        st.write(f"DEBUG: Gravando {nova_data_iso} para o ID {st.session_state.user.id}")
                        
                        # 3. Executa a atualização no Supabase
                        res = supabase.table("profiles").update({
                            "status_assinatura": "ativo",
                            "data_vencimento": nova_data_iso
                        }).eq("id", st.session_state.user.id).execute()
                        
                        # 4. Atualiza a sessão local
                        st.session_state.perfil['status_assinatura'] = 'ativo'
                        st.session_state.perfil['data_vencimento'] = nova_data_iso
                        
                        st.success(f"✅ Acesso libertado por {dias_adicionais} dias!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao gravar no banco: {e}")
                else:
                    st.warning("Pagamento não encontrado. Verifique o e-mail ou aguarde o banco compensar.")
                    st.stop() # <-- Impede carregamento do resto das abas

# --- SE O USUÁRIO TEM ACESSO, MOSTRA O SISTEMA NORMAL ---
aba = st.radio("Navegação:", ["⚙️ Perfil", "🏠 Cargas", "💡 Luminotecnica", "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"], horizontal=True)

# --- MÓDULO PERFIL ---
if aba == "⚙️ Perfil":
    st.header("⚙️ Configurações do Técnico")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.perfil['nome_empresa'] = st.text_input("Empresa:", value=st.session_state.perfil.get('nome_empresa', ''))
        st.session_state.perfil['crt']          = st.text_input("CRT/CFT:", value=st.session_state.perfil.get('crt', ''))
        st.session_state.perfil['telefone']     = st.text_input("WhatsApp:", value=st.session_state.perfil.get('telefone', ''))
    with c2:
        st.session_state.perfil['cnpj']          = st.text_input("CNPJ:", value=st.session_state.perfil.get('cnpj', ''))
        st.session_state.perfil['email_contato'] = st.text_input("E-mail Profissional:", value=st.session_state.perfil.get('email_contato', ''))
        st.session_state.perfil['endereco']      = st.text_input("Cidade/UF:", placeholder="Ex: Araxá - MG", value=st.session_state.perfil.get('endereco', ''))

    if st.button("💾 Salvar na Nuvem"):
        salvar_perfil_supabase()

    # --- ÁREA DE UPGRADE COM VALORES EM DESTAQUE E BOTÃO DE VERIFICAÇÃO ---
    if st.session_state.perfil.get('status_assinatura') != 'ativo':
        st.divider()
        st.subheader("💎 Escolha seu Plano Premium")
        st.write("Libere todos os módulos e relatórios personalizados.")
        
        c_up1, c_up2, c_up3 = st.columns(3)
        with c_up1:
            st.info("**Plano Mensal**")
            st.markdown("### R$ 19,90")
            st.caption("Acesso total mês a mês")
            st.link_button("💳 Assinar Mensal", LINKS_MERCADO_PAGO["mensal"], use_container_width=True)
        with c_up2:
            st.success("**Plano Trimestral**")
            st.markdown("### R$ 49,90")
            st.caption("Equivale a R$ 16,63/mês")
            st.link_button("💳 Assinar Trimestral", LINKS_MERCADO_PAGO["trimestral"], type="primary", use_container_width=True)
        with c_up3:
            st.warning("**Plano Anual**")
            st.markdown("### R$ 149,90")
            st.caption("Equivale a R$ 12,49/mês")
            st.link_button("💳 Assinar Anual", LINKS_MERCADO_PAGO["anual"], use_container_width=True)

        st.divider()
        st.write("Já realizou o pagamento? Clique abaixo para liberar seu acesso.")
        
        # Botão com chave única e lógica de gravação corrigida
        if st.button("🔄 Verificar Pagamento e Liberar Acesso", type="primary", use_container_width=True, key="btn_perfil_verificar"):
            with st.spinner("Consultando o servidor do Mercado Pago..."):
                pago, dias_adicionais = verificar_pagamento_direto_mp(st.session_state.user.email)
                
                if pago:
                    try:
                        # 1. Calcula a nova data de vencimento
                        nova_data = datetime.now(timezone.utc) + timedelta(days=dias_adicionais)
                        nova_data_iso = nova_data.isoformat()
                        
                        # 2. Usa a conexão AUTENTICADA para o Supabase
                        cliente_auth = get_supabase_autenticado()
                        
                        # 3. Envia o status e a data limite para o banco
                        cliente_auth.table("profiles").update({
                            "status_assinatura": "ativo",
                            "data_vencimento": nova_data_iso
                        }).eq("id", st.session_state.user.id).execute()
                        
                        # 4. Atualiza a sessão local do Streamlit
                        st.session_state.perfil['status_assinatura'] = 'ativo'
                        st.session_state.perfil['data_vencimento'] = nova_data_iso
                        
                        st.success(f"✅ Sucesso! Acesso liberado por {dias_adicionais} dias. Reiniciando o sistema...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar a base de dados: {e}")
                else:
                    st.warning("Nenhum pagamento aprovado encontrado para este e-mail ainda.")
# --- MÓDULO CARGAS ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento Profissional (NBR 5410 + Materiais)")

    with st.expander("🔌 Configuração da Rede e Concessionária", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            concessionaria = st.selectbox("Selecione a Concessionária:",
                                           ["CEMIG (MG)", "CPFL (SP)", "ENEL (RJ/SP)", "EQUATORIAL", "Outra (Manual)"])
        with col_c2:
            tensao_fase = st.selectbox("Tensão Fase-Neutro (V):", [127, 220], index=0)

    if st.session_state.dados_cargas.columns.tolist() != ["Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Watts)"]:
        st.session_state.dados_cargas = pd.DataFrame({
            "Comodo": ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro"],
            "Area (m2)": [15.0, 10.0, 12.0, 10.0, 4.5],
            "Perimetro (m)": [16.0, 13.0, 14.0, 13.0, 9.0],
            "Iluminacao (VA)": ["-", "-", "-", "-", "-"],
            "TUG (Qtd)": [0, 0, 0, 0, 0],
            "Potencia TUG (VA)": [0.0, 0.0, 0.0, 0.0, 0.0],
            "TUE (Watts)": [0.0, 0.0, 0.0, 0.0, 5500.0]
        })

    st.subheader("1. Entrada de Dados e Medidas")
    df_editor = st.data_editor(
        st.session_state.dados_cargas,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_cargas_v1"
    )

    if st.button("⚡ Calcular Projeto e Dimensionar Circuitos", type="primary", use_container_width=True):
        st.session_state.dados_cargas = df_editor.copy()
        df_calc = df_editor.copy()
        novos_circuitos = []
        pot_ilum_total = 0
        pot_tug_total = 0

        cabos = {
            "1.5mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "2.5mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "4.0mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "6.0mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "10.0mm2": {"Fase": 0, "Neutro": 0, "Terra": 0},
        }

        for i, r in df_calc.iterrows():
            try:
                a = float(r["Area (m2)"] or 0)
                p = float(r["Perimetro (m)"] or 0)
                
                if a <= 0 or p <= 0:
                    st.warning(f"⚠️ Linha {i}: Área ou perímetro inválido. Pulando...")
                    continue
                
                nome = str(r["Comodo"]).lower()

                va_ilum = 100 if a <= 6 else 100 + (math.floor((a - 6) / 4) * 60)
                qtd_lamp = max(math.ceil(va_ilum / 100), 1)
                df_calc.at[i, "Iluminacao (VA)"] = f"{qtd_lamp} pt ({va_ilum}VA)"
                pot_ilum_total += va_ilum

                comp_15 = p + (qtd_lamp * 3.5)
                cabos["1.5mm2"]["Fase"]  += comp_15 * 1.5
                cabos["1.5mm2"]["Neutro"] += comp_15

                is_molhada  = any(x in nome for x in ["cozinha", "banheiro", "servico", "lavanderia", "copa", "wc"])
                is_banheiro = any(x in nome for x in ["banheiro", "wc", "suite"])

                if is_banheiro:
                    q_tugs, p_tugs = 1, 600
                else:
                    div    = 3.5 if is_molhada else 5.0
                    q_tugs = max(math.ceil(p / div), 1)
                    p_tugs = (min(q_tugs, 3) * 600 + max(0, q_tugs - 3) * 100) if is_molhada else q_tugs * 100

                df_calc.at[i, "TUG (Qtd)"]        = int(q_tugs)
                df_calc.at[i, "Potencia TUG (VA)"] = float(p_tugs)
                pot_tug_total += p_tugs

                comp_25 = p + (q_tugs * 1.5)
                cabos["2.5mm2"]["Fase"]  += comp_25
                cabos["2.5mm2"]["Neutro"] += comp_25
                cabos["2.5mm2"]["Terra"]  += comp_25

                tue_w = float(r["TUE (Watts)"] or 0)
                if tue_w > 0:
                    v_tue    = 220 if (tue_w >= 4000 or tensao_fase == 220) else 127
                    corrente = tue_w / v_tue

                    if corrente <= 21:   bitola = "2.5mm2"
                    elif corrente <= 28: bitola = "4.0mm2"
                    elif corrente <= 36: bitola = "6.0mm2"
                    else:                bitola = "10.0mm2"

                    disjuntor = "20A" if corrente <= 16 else ("25A" if corrente <= 21 else ("32A" if corrente <= 28 else "40A"))
                    tipo_disj = "Bipolar" if v_tue == 220 else "Unipolar"

                    novos_circuitos.append({
                        "Circ": f"C{len(novos_circuitos)+3:02d}",
                        "Descricao": f"TUE - {r['Comodo']}",
                        "Potencia": f"{tue_w:.0f}W",
                        "Tensao": f"{v_tue}V",
                        "Cabo": bitola,
                        "Disjuntor": disjuntor,
                        "Tipo Disj.": tipo_disj
                    })

                    comp_tue = (p / 2) + 4.0
                    if v_tue == 220 and tensao_fase == 127:
                        cabos[bitola]["Fase"]  += comp_tue * 2
                        cabos[bitola]["Terra"] += comp_tue
                    else:
                        cabos[bitola]["Fase"]  += comp_tue
                        cabos[bitola]["Neutro"] += comp_tue
                        cabos[bitola]["Terra"]  += comp_tue

            except Exception as e:
                st.warning(f"⚠️ Erro na linha {i}: {e}")
                continue

        if pot_ilum_total > 0:
            novos_circuitos.insert(0, {"Circ": "C01", "Descricao": "Iluminacao Geral",
                "Potencia": f"{pot_ilum_total}VA", "Tensao": f"{tensao_fase}V",
                "Cabo": "1.5mm2", "Disjuntor": "10A", "Tipo Disj.": "Unipolar"})
        if pot_tug_total > 0:
            novos_circuitos.insert(1, {"Circ": "C02", "Descricao": "Tomadas Gerais (TUGs)",
                "Potencia": f"{pot_tug_total}VA", "Tensao": f"{tensao_fase}V",
                "Cabo": "2.5mm2", "Disjuntor": "20A", "Tipo Disj.": "Unipolar"})

        materiais_dinamicos = []
        for bitola, vias in cabos.items():
            if vias["Fase"]  > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Fase/Retorno)",  "Qtd": f"{math.ceil(vias['Fase'])}m"})
            if vias["Neutro"] > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Neutro - Azul)", "Qtd": f"{math.ceil(vias['Neutro'])}m"})
            if vias.get("Terra", 0) > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Terra - Verde)", "Qtd": f"{math.ceil(vias['Terra'])}m"})

        contagem_disj = {}
        for c in novos_circuitos:
            dj   = c.get("Disjuntor")
            tipo = c.get("Tipo Disj.", "Unipolar")
            if dj:
                nome_dj = f"Disjuntor DIN {tipo} {dj}"
                contagem_disj[nome_dj] = contagem_disj.get(nome_dj, 0) + 1
        for nome_dj, qtd in contagem_disj.items():
            materiais_dinamicos.append({"Item": nome_dj, "Qtd": f"{qtd} un"})

        total_circ = len(novos_circuitos)
        tam_qdc    = 12 if total_circ <= 6 else (16 if total_circ <= 12 else 24)
        materiais_dinamicos.append({"Item": f"Quadro de Distribuicao (QDC) - {tam_qdc} Polos", "Qtd": "1 un"})

        st.session_state.lista_circuitos  = novos_circuitos
        st.session_state.resumo_materiais = materiais_dinamicos
        st.success("✅ Cálculos e materiais gerados com sucesso!")
        st.rerun()

    if st.session_state.lista_circuitos:
        st.divider()
        st.subheader("⚡ Quadro de Circuitos Sugerido (QDC)")
        st.table(pd.DataFrame(st.session_state.lista_circuitos))
        st.subheader("📦 Lista Estimada de Materiais")
        st.table(pd.DataFrame(st.session_state.resumo_materiais))
        st.info("💡 Dica: Verifique sempre a bitola do cabo no 'Dimensionador' antes de fechar o pedido.")

        if st.button("📄 Gerar Memorial Técnico Completo (PDF)", use_container_width=True):
            try:
                hoje = datetime.now()
                validade = hoje + timedelta(days=7)
                hoje_str = hoje.strftime('%d/%m/%Y %H:%M')
                validade_str = validade.strftime('%d/%m/%Y')

                pdf = FPDF()
                pdf.add_page()
                montar_cabecalho_pdf(pdf)

                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 6, f"Gerado em: {hoje_str} | Rede: {tensao_fase}V", 0, 1, "R")
                # --- ADICIONADO VALIDADE NO MEMORIAL ---
                pdf.set_text_color(255, 0, 0)
                pdf.set_font("Arial", "BI", 8)
                pdf.cell(0, 5, f"VÁLIDO ATÉ: {validade_str}", 0, 1, "R")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)

                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "1. MEMORIAL DE DIMENSIONAMENTO DE CARGAS", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                h_c = ["Comodo", "Area", "Iluminacao", "TUGs", "Pot.TUG", "TUE"]
                w_c = [45, 20, 35, 20, 35, 35]
                for h, w in zip(h_c, w_c):
                    pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for _, r in st.session_state.dados_cargas.iterrows():
                    pdf.cell(45, 7, limpar_texto(str(r["Comodo"])), 1)
                    pdf.cell(20, 7, f"{r['Area (m2)']}m2", 1, 0, "C")
                    pdf.cell(35, 7, limpar_texto(str(r["Iluminacao (VA)"])), 1, 0, "C")
                    pdf.cell(20, 7, str(r["TUG (Qtd)"]), 1, 0, "C")
                    pdf.cell(35, 7, f"{r['Potencia TUG (VA)']}VA", 1, 0, "C")
                    pdf.cell(35, 7, f"{r['TUE (Watts)']}W", 1, 1, "C")

                pdf.ln(8)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "2. QUADRO DE DISTRIBUICAO (QDC)", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                h_q = ["Circ.", "Descricao", "Potencia", "Tensao", "Cabo", "Disj.", "Tipo"]
                w_q = [15, 55, 25, 20, 25, 20, 30]
                for h, w in zip(h_q, w_q):
                    pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for c in st.session_state.lista_circuitos:
                    pdf.cell(15, 7, limpar_texto(c["Circ"]), 1, 0, "C")
                    pdf.cell(55, 7, limpar_texto(c["Descricao"]), 1)
                    pdf.cell(25, 7, limpar_texto(c["Potencia"]), 1, 0, "C")
                    pdf.cell(20, 7, limpar_texto(c["Tensao"]), 1, 0, "C")
                    pdf.cell(25, 7, limpar_texto(c["Cabo"]), 1, 0, "C")
                    pdf.cell(20, 7, limpar_texto(c["Disjuntor"]), 1, 0, "C")
                    pdf.cell(30, 7, limpar_texto(c.get("Tipo Disj.", "")), 1, 1, "C")

                pdf.ln(8)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "3. MATERIAIS SUGERIDOS (ESTIMATIVA INFRAESTRUTURA)", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(140, 8, "Item e Especificacao", 1, 0, "C", True)
                pdf.cell(50, 8, "Qtd", 1, 1, "C", True)
                pdf.set_font("Arial", "", 8)
                for m in st.session_state.resumo_materiais:
                    pdf.cell(140, 7, limpar_texto(m["Item"]), 1)
                    pdf.cell(50, 7, limpar_texto(m["Qtd"]), 1, 1, "C")

                pdf_out = pdf.output(dest="S").encode("latin-1", "ignore")
                st.download_button("⬇️ Baixar Projeto Completo (PDF)", pdf_out, "Projeto_Eletrico.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Erro no PDF: {e}")

# --- MÓDULO Luminotecnica  ---
elif aba == "💡 Luminotecnica":
    st.header("💡 Dimensionamento Luminotécnico (NBR ISO/CIE 8995-1)")
    st.info("Este módulo utiliza o Método dos Lúmens para calcular a quantidade de luminárias necessária.")

    with st.expander("🏠 Dados do Ambiente", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            comprimento = st.number_input("Comprimento (m):", min_value=0.1, value=5.0, key="lum_comp")
            largura = st.number_input("Largura (m):", min_value=0.1, value=4.0, key="lum_larg")
        with c2:
            h_total = st.number_input("Pé direito total (m):", min_value=0.1, value=3.0, key="lum_h_total")
            h_trabalho = st.number_input("Altura do plano de trabalho (m):", min_value=0.0, value=0.75, help="Mesa: 0.75m | Chão: 0.0m", key="lum_h_trab")
        with c3:
            h_luminaria = st.number_input("Altura da luminária ao teto (m):", min_value=0.0, value=0.0, help="Embutida: 0.0m", key="lum_h_lum")
        
        h_util = h_total - h_trabalho - h_luminaria
        area_total = comprimento * largura
        st.write(f"**Área Total:** {area_total:.2f} m² | **Altura Útil (h):** {h_util:.2f} m")

    with st.expander("📚 Parâmetros Normativos"):
        col1, col2 = st.columns(2)
        with col1:
            lux_sugerido = st.selectbox("Tipo de Ambiente (Lux):", [
                "Escritório / Sala de Estudo (500 lux)",
                "Cozinha / Banheiro (300 lux)",
                "Quarto / Sala (150 lux)",
                "Corredor / Depósito (100 lux)",
                "Oficina / Indústria (750 lux)",
                "Personalizado"
            ], key="lum_lux_select")
            
            if lux_sugerido == "Personalizado":
                nivel_iluminancia = st.number_input("Nível de Iluminância desejado (Lux):", value=500, key="lum_lux_custom")
            else:
                nivel_iluminancia = int(lux_sugerido.split('(')[1].split(' ')[0])

        with col2:
            fator_utilizacao = st.slider("Fator de Utilização (η):", 0.1, 1.0, 0.5, help="Depende da luminária e cores das paredes.", key="lum_fu")
            fator_perdas = st.select_slider("Fator de Manutenção (Limpeza):", options=[0.6, 0.7, 0.8], value=0.8, help="0.8: Limpo | 0.7: Médio | 0.6: Sujo", key="lum_fm")

    with st.expander("🔦 Especificações da Lâmpada/Luminária"):
        c1, c2 = st.columns(2)
        with c1:
            fluxo_unitario = st.number_input("Fluxo Luminoso por Luminária (Lúmens):", min_value=1, value=2500, help="Ver no catálogo do fabricante", key="lum_fluxo_u")
        with c2:
            potencia_unit = st.number_input("Potência por Luminária (W):", min_value=1, value=24, key="lum_pot_u")

    fluxo_total_necessario = (nivel_iluminancia * area_total) / (fator_utilizacao * fator_perdas)
    quantidade_n = fluxo_total_necessario / fluxo_unitario
    quantidade_final = int(-(-quantidade_n // 1))
    
    potencia_total = quantidade_final * potencia_unit
    densidade_potencia = potencia_total / area_total if area_total > 0 else 0

    st.subheader("📊 Resultado do Dimensionamento")
    res1, res2, res3 = st.columns(3)
    res1.metric("Qtd. de Luminárias", f"{quantidade_final} un")
    res2.metric("Potência Total", f"{potencia_total} W")
    res3.metric("W/m²", f"{densidade_potencia:.2f}")

    st.write("---")
    st.subheader("📐 Sugestão de Distribuição")
    proporcao = comprimento / largura
    colunas = math.sqrt(quantidade_final * proporcao)
    linhas = quantidade_final / colunas if colunas > 0 else 1
    
    st.write(f"Para uma distribuição uniforme, tente instalar em uma malha de aproximadamente:")
    st.info(f"**{round(colunas)} luminárias ao longo do comprimento** x **{round(linhas)} luminárias ao longo da largura**.")

    dados_atuais = {
        "nivel_lux": nivel_iluminancia,
        "qtd_luminarias": quantidade_final,
        "potencia_total": potencia_total,
        "area": area_total,
        "distribuicao": f"{round(colunas)}x{round(linhas)}"
    }

    try:
        pdf_bytes = gerar_pdf_resultado_lumino(dados_atuais, st.session_state.get('perfil', {}))
        if pdf_bytes:
            st.download_button(
                label="📥 Gerar e Baixar Relatório (PDF)",
                data=pdf_bytes,
                file_name=f"Luminotecnico_{st.session_state.perfil.get('nome_empresa', 'VoltSpec')}.pdf",
                mime="application/pdf",
                key="btn_download_lumino"
            )
    except Exception as e:
        st.error(f"Erro ao preparar o PDF: {e}")

# --- MÓDULO ORÇAMENTOS ---
elif aba == "💰 Orçamentos":
    st.header("💰 Orçamentos de Serviços")
    cliente = st.text_input("Nome do Cliente:", "Cliente Araxá")
    servicos = [
        {"Descricao": "Ponto de Tomada / Interruptor", "Qtd": 0, "Preco": 85.0},
        {"Descricao": "Ponto de Iluminacao",            "Qtd": 0, "Preco": 75.0},
        {"Descricao": "Montagem de Quadro (ate 12 disj.)",    "Qtd": 0, "Preco": 450.0},
        {"Descricao": "Montagem de Quadro (acima 12 disj.)",  "Qtd": 0, "Preco": 650.0},
        {"Descricao": "Padrao CEMIG Monofasico",        "Qtd": 0, "Preco": 850.0},
        {"Descricao": "Padrao CEMIG Trifasico",          "Qtd": 0, "Preco": 1350.0},
        {"Descricao": "Instalacao de Chuveiro",          "Qtd": 0, "Preco": 110.0},
        {"Descricao": "Laudo de Conformidade",           "Qtd": 0, "Preco": 350.0}
    ]
    df_serv = st.data_editor(pd.DataFrame(servicos), num_rows="dynamic", use_container_width=True, key="orc_edt")

    total_orc = (df_serv["Qtd"] * df_serv["Preco"]).sum()
    st.subheader(f"Total Serviços: R$ {total_orc:,.2f}")

    if st.button("📄 Gerar PDF Orçamento"):
        pdf = gerar_pdf_universal(f"ORCAMENTO - {cliente}", df_serv, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", pdf, "Orcamento.pdf", "application/pdf")

# --- MÓDULO MATERIAIS ---
elif aba == "📦 Materiais":
    st.header("📦 Lista de Materiais Elétricos")
    materiais = [
        {"Descricao": "Cabo Flexivel 2,5mm (Rolo 100m)", "Qtd": 0, "Preco": 285.0},
        {"Descricao": "Cabo Flexivel 4,0mm (Rolo 100m)", "Qtd": 0, "Preco": 420.0},
        {"Descricao": "Disjuntor DIN Mono (10A a 32A)",  "Qtd": 0, "Preco": 19.90},
        {"Descricao": "Dispositivo DR Bipolar 40A",       "Qtd": 0, "Preco": 189.0},
        {"Descricao": "Dispositivo DPS 20kA",             "Qtd": 0, "Preco": 58.0},
        {"Descricao": "Caixa de Passagem 4x2",            "Qtd": 0, "Preco": 3.50},
        {"Descricao": "Eletroduto Corrugado 3/4 (50m)",   "Qtd": 0, "Preco": 75.0}
    ]
    df_mat = st.data_editor(pd.DataFrame(materiais), num_rows="dynamic", use_container_width=True, key="mat_edt")

    total_mat = (df_mat["Qtd"] * df_mat["Preco"]).sum()
    st.subheader(f"Total Materiais: R$ {total_mat:,.2f}")
    st.info("💡 Dica: Verifique sempre a bitola do cabo no 'Dimensionador' antes de fechar o pedido.")

    if st.button("📄 Gerar PDF Materiais"):
        pdf = gerar_pdf_universal("LISTA DE MATERIAIS", df_mat, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", pdf, "Materiais.pdf", "application/pdf")

# --- MÓDULO DIMENSIONADOR ---
elif aba == "📐 Dimensionador":
    st.header("📐 Cálculo Técnico Profissional (NBR 5410)")

    col_inp1, col_inp2, col_inp3 = st.columns(3)
    with col_inp1:
        pot       = st.number_input("Potência Total (W):", value=1200.0, step=100.0)
        tipo_carga = st.selectbox("Tipo de Carga:", ["Iluminação", "Tomadas (Geral/TUE)"])
    with col_inp2:
        tensao = st.selectbox("Tensão (V):", [127, 220])
        dist   = st.number_input("Distância do Quadro (m):", value=15.0, step=1.0)
    with col_inp3:
        fator_agrup = st.slider("Fator de Agrupamento:", 0.4, 1.0, 1.0, help="0.70 para 3 circuitos no mesmo conduíte")

    ib = pot / tensao
    ib_corrigida = ib / fator_agrup
    bitola_minima = 1.5 if tipo_carga == "Iluminação" else 2.5

    if ib_corrigida <= 15.5:   bitola_sugerida = 1.5
    elif ib_corrigida <= 21:   bitola_sugerida = 2.5
    elif ib_corrigida <= 28:   bitola_sugerida = 4.0
    elif ib_corrigida <= 36:   bitola_sugerida = 6.0
    else:                      bitola_sugerida = 10.0

    bitola_final     = max(bitola_sugerida, bitola_minima)
    queda_v          = (2 * dist * ib * 0.0172) / bitola_final
    percentual_queda = (queda_v / tensao) * 100 if tensao > 0 else 0

    st.divider()
    c_res1, c_res2, c_res3 = st.columns(3)
    with c_res1:
        st.metric("Corrente de Projeto (Ib)", f"{ib:.2f} A")
        if fator_agrup < 1:
            st.caption(f"Ib Corrigida (Agrup.): {ib_corrigida:.2f} A")
    with c_res2:
        color = "normal" if percentual_queda <= 4.0 else "inverse"
        st.metric("Queda de Tensão", f"{percentual_queda:.2f} %", delta=f"{queda_v:.2f} V", delta_color=color)
    with c_res3:
        st.metric("Bitola Final", f"{bitola_final} mm²")

    st.subheader("🛡️ Verificação de Conformidade")
    erros, avisos = [], []
    if bitola_sugerida < bitola_minima:
        avisos.append(f"A norma exige mínimo de {bitola_minima}mm² para {tipo_carga.lower()}.")
    if percentual_queda > 4.0:
        erros.append("Queda de tensão acima de 4% (Limite NBR 5410 para circuitos terminais).")

    disjuntor_sugerido = math.ceil(ib / 5) * 5
    if disjuntor_sugerido < 10:
        disjuntor_sugerido = 10

    if not erros and not avisos:
        st.success("✅ Circuito em conformidade com a NBR 5410.")
    else:
        for erro in erros:   st.error(f"❌ **CONFORMIDADE:** {erro}")
        for aviso in avisos: st.warning(f"⚠️ **OBSERVAÇÃO:** {aviso}")

    with st.expander("📝 Detalhes do Dimensionamento"):
        st.write(f"""
        - **Cabo:** Cobre com isolação em PVC (70°C).
        - **Método de Instalação:** Condutos embutidos em alvenaria (B1).
        - **Resistividade (ρ):** 0.0172 Ω·mm²/m.
        - **Disjuntor Sugerido:** {disjuntor_sugerido}A (Curva B para iluminação, C para motores/TUE).
        """)

# --- MÓDULO PRODUTOS ---
elif aba == "🛒 Produtos":
    st.header("🛒 Vitrine de Ferramentas (Mercado Livre)")
    prods = [
        {"nome": "Jogo Chaves Isoladas",                     "img": "https://http2.mlstatic.com/D_NQ_NP_2X_701755-MLB85959666529_062025-F.webp",  "link": "https://meli.la/2xLSiQJ"},
        {"nome": "Alicate Decapador Vonder",                 "img": "https://http2.mlstatic.com/D_NQ_NP_2X_608489-MLA99480826142_112025-F.webp",  "link": "https://meli.la/2L47LTv"},
        {"nome": "Bolsa Ferramentas Reforcada",              "img": "https://http2.mlstatic.com/D_NQ_NP_2X_947240-MLA99992405049_112025-F.webp",  "link": "https://meli.la/1E4on12"},
        {"nome": "Alicate Crimpar Prensa",                   "img": "https://http2.mlstatic.com/D_NQ_NP_2X_928036-MLA99440131490_112025-F.webp",  "link": "https://meli.la/247XSK7"},
        {"nome": "Kit Eletrica Chave Teste + Caneta",        "img": "https://http2.mlstatic.com/D_NQ_NP_2X_925244-MLA102644904043_122025-F.webp", "link": "https://meli.la/214x31Y"},
        {"nome": "Alicate Universal Eletricista 1000V",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_718013-MLA96100316665_102025-F.webp",  "link": "https://meli.la/14aG1bU"},
        {"nome": "Cinto Pochete Porta Ferramentas",          "img": "https://http2.mlstatic.com/D_NQ_NP_2X_993974-MLA96427705692_102025-F.webp",  "link": "https://meli.la/1RKgafT"},
        {"nome": "Cinturao Eletricista Multifuncional",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_798036-MLB106606586781_022026-F.webp", "link": "https://meli.la/1JcRtAG"},
    ]
    cols = st.columns(4)
    for i, p in enumerate(prods):
        with cols[i % 4]:
            st.image(p["img"], use_container_width=True)
            st.write(f"**{p['nome']}**")
            st.link_button("🚀 Ver no Mercado Livre", p["link"], use_container_width=True)

# --- 8. RODAPÉ ---
st.markdown("---")
c_ft1, c_ft2, c_ft3 = st.columns(3)
with c_ft1:
    st.caption(f"📍 {st.session_state.perfil.get('endereco', '')}")
with c_ft2:
    st.caption("⚡ Desenvolvido por Spec Pro")
with c_ft3:
    if st.session_state.get('user'):
        st.caption(f"🔑 Logado como: {st.session_state.user.email}")