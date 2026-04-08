import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
from supabase import create_client, Client
import streamlit as st

st.set_page_config(
    page_title="VoltSpec Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed" # Melhora a visão no celular ao abrir
)

# Forçar o modo 'Standalone' (abre como app, sem barra de endereço)
st.markdown("""
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="application-name" content="VoltSpec Pro">
    <meta name="apple-mobile-web-app-title" content="VoltSpec Pro">
    <meta name="theme-color" content="#000000">
    <meta name="msapplication-navbutton-color" content="#000000">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    """, unsafe_allow_html=True)

# --- 1. CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA) ---
st.set_page_config(
    page_title="VoltSpec Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de CSS para esconder botões do Streamlit e parecer App nativo
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
# --- 2. CONEXÃO COM BANCO (SUPABASE) ---
URL_SUPA = "https://drhcokdzqycmdkshceub.supabase.co"
KEY_SUPA = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyaGNva2R6cXljbWRrc2hjZXViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyNjA0MDQsImV4cCI6MjA5MDgzNjQwNH0.FrN2x_Tgq8m_ZIYCt6Ht0R3dMU3_RQUwGLAw3Pfgbm0"

def init_connection():
    try:
     return create_client(URL_SUPA, KEY_SUPA)
    except Exception as e:
        st.error(f"❌ Erro na conexão com o Supabase: {e}")
        return

supabase = init_connection()

# --- 3. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---

def limpar_texto(txt):
    """Remove emojis e caracteres especiais que travam o FPDF latin-1"""
    if not txt: return ""
    return str(txt).encode('latin-1', 'ignore').decode('latin-1').replace("²", "2").strip()

def gerar_pdf_universal(titulo, df_dados, colunas_w, headers, tipo="tabela"):
    """Gera PDF para Orçamentos ou Materiais"""
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Estilizado
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, limpar_texto(st.session_state.get('nome_empresa', 'VoltSpec Pro')), ln=True, align="C")
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(190, 5, limpar_texto(f"Registro: {st.session_state.get('crt', '')} | Tel: {st.session_state.get('telefone', '')}"), ln=True, align="C")
    pdf.ln(15)
    
    # Título e Data
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"RELATORIO: {titulo}", "B", 1, "L")
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "R")
    pdf.ln(5)
    
    # Tabela
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 9)
    for i, h in enumerate(headers):
        pdf.cell(colunas_w[i], 8, h, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 8)
    total = 0
    for _, r in df_dados.iterrows():
        if r.get("Qtd", 0) > 0:
            sub = r["Qtd"] * r["Preço"]
            total += sub
            pdf.cell(colunas_w[0], 7, limpar_texto(r["Descrição"]), 1)
            pdf.cell(colunas_w[1], 7, str(r["Qtd"]), 1, 0, "C")
            pdf.cell(colunas_w[2], 7, f"{r['Preço']:.2f}", 1, 0, "C")
            pdf.cell(colunas_w[3], 7, f"{sub:.2f}", 1, 1, "C")
            
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", 0, 1, "R")
    
    return pdf.output(dest="S").encode("latin-1")

# --- 4. FUNÇÕES DE BANCO DE DADOS ---

def carregar_perfil_supabase():
    if 'user' in st.session_state and st.session_state.user:
        try:
            res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
            if res.data:
                d = res.data[0]
                st.session_state.nome_empresa = d.get('nome_empresa', '')
                st.session_state.crt = d.get('crt', '')
                st.session_state.telefone = d.get('telefone', '')
                st.session_state.cnpj = d.get('cnpj', '')
                st.session_state.endereco = d.get('endereco', '')
                st.session_state.email_contato = d.get('email_contato', '')
        except: pass

def salvar_perfil_supabase():
    try:
        dados = {
            "id": st.session_state.user.id,
            "nome_empresa": st.session_state.nome_empresa,
            "crt": st.session_state.crt,
            "telefone": st.session_state.telefone,
            "cnpj": st.session_state.cnpj,
            "endereco": st.session_state.endereco,
            "email_contato": st.session_state.email_contato,
            "email": st.session_state.user.email
        }
        supabase.table("profiles").upsert(dados).execute()
        st.success("✅ Sincronizado!")
    except Exception as e: st.error(f"Erro: {e}")

# --- 5. ESTADO INICIAL ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user' not in st.session_state: st.session_state.user = None
if 'dados_cargas' not in st.session_state:
    st.session_state.dados_cargas = pd.DataFrame([{
        "Cômodo": "Sala", "Tipo": "Social", "Área (m²)": 0.0, "Perímetro (m)": 0.0, 
        "Iluminação (VA/Lâmp.)": "0 VA", "TUG (Qtd)": 0, "Potência TUG (VA)": 0, "TUE (Watts)": 0
    }])

# --- 6. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("⚡ VoltSpec Pro")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        em = st.text_input("E-mail")
        pw = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
                if res.user:
                    st.session_state.user = res.user
                    st.session_state.logado = True
                    carregar_perfil_supabase()
                    st.rerun()
            except: st.error("Falha no login.")
    with t2:
        nem = st.text_input("Novo E-mail")
        npw = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": nem, "password": npw})
                st.success("Sucesso! Verifique seu e-mail.")
            except: st.error("Erro no cadastro.")
    st.stop()

# --- 7. SISTEMA ---
st.sidebar.title("VoltSpec Pro ⚡")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

aba = st.radio("Navegação:", ["⚙️ Perfil", "🏠 Cargas", "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"], horizontal=True)

# --- MÓDULO PERFIL ---
if aba == "⚙️ Perfil":
    st.header("⚙️ Configurações do Técnico")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.nome_empresa = st.text_input("Empresa:", value=st.session_state.get('nome_empresa', ''))
        st.session_state.crt = st.text_input("CRT/CFT:", value=st.session_state.get('crt', ''))
        st.session_state.telefone = st.text_input("WhatsApp:", value=st.session_state.get('telefone', ''))
    with c2:
        st.session_state.cnpj = st.text_input("CNPJ:", value=st.session_state.get('cnpj', ''))
        st.session_state.email_contato = st.text_input("E-mail Profissional:", value=st.session_state.get('email_contato', ''))
        st.session_state.endereco = st.text_input("Cidade/UF:", value=st.session_state.get('endereco', 'Araxá - MG'))
    
    if st.button("💾 Salvar na Nuvem"): salvar_perfil_supabase()

# --- MÓDULO CARGAS ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento Profissional (NBR 5410 + Materiais)")

    # 1. SELEÇÃO DE CONCESSIONÁRIA E REDE
    with st.expander("🔌 Configuração da Rede e Concessionária", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            concessionaria = st.selectbox("Selecione a Concessionária:", 
                                        ["CEMIG (MG)", "CPFL (SP)", "ENEL (RJ/SP)", "EQUATORIAL", "Outra (Manual)"])
        with col_c2:
            tensao_fase = st.selectbox("Tensão Fase-Neutro (V):", [127, 220], index=0)

    # 2. ESTRUTURA DA PLANILHA (Corrigido para aceitar texto na Iluminação)
    if 'dados_cargas' not in st.session_state:
        st.session_state.dados_cargas = pd.DataFrame({
            "Cômodo": ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro"],
            "Área (m²)": [15.0, 10.0, 12.0, 10.0, 4.5],
            "Perímetro (m)": [16.0, 13.0, 14.0, 13.0, 9.0],
            "Iluminação (VA)": ["-", "-", "-", "-", "-"], # Iniciado como texto para não sumir
            "TUG (Qtd)": [0, 0, 0, 0, 0],
            "Potência TUG (VA)": [0.0, 0.0, 0.0, 0.0, 0.0],
            "TUE (Watts)": [0.0, 0.0, 0.0, 0.0, 5500.0]
        })
    
    if 'lista_circuitos' not in st.session_state: st.session_state.lista_circuitos = []
    if 'resumo_materiais' not in st.session_state: st.session_state.resumo_materiais = []

    # 3. EDITOR DE DADOS
    st.subheader("1. Entrada de Dados e Medidas")
    df_editor = st.data_editor(
        st.session_state.dados_cargas,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_cargas_vFinal_Pro3"
    )

    # 4. LÓGICA DE CÁLCULO NBR 5410
    if st.button("⚡ Calcular Projeto e Dimensionar Circuitos", type="primary", use_container_width=True):
        df_calc = df_editor.copy()
        novos_circuitos = []
        
        pot_ilum_total = 0
        pot_tug_total = 0
        
        # Dicionário para acumular os cabos por bitola e via
        cabos = {
            "1.5mm²": {"Fase": 0, "Neutro": 0, "Terra": 0},
            "2.5mm²": {"Fase": 0, "Neutro": 0, "Terra": 0},
            "4.0mm²": {"Fase": 0, "Neutro": 0, "Terra": 0},
            "6.0mm²": {"Fase": 0, "Neutro": 0, "Terra": 0},
            "10.0mm²": {"Fase": 0, "Neutro": 0, "Terra": 0}
        }
        
        for i, r in df_calc.iterrows():
            try:
                a = float(r["Área (m²)"])
                p = float(r["Perímetro (m)"])
                nome = str(r["Cômodo"]).lower()

                # --- CÁLCULO ILUMINAÇÃO (NBR 5410) ---
                if a <= 6:
                    va_ilum = 100
                else:
                    va_ilum = 100 + (math.floor((a - 6) / 4) * 60)
                
                qtd_lamp = max(math.ceil(va_ilum / 100), 1)
                df_calc.at[i, "Iluminação (VA)"] = f"{qtd_lamp} pt ({va_ilum}VA)"
                pot_ilum_total += va_ilum
                
                # Estimativa Cabos 1.5mm² (Iluminação)
                comp_15 = p + (qtd_lamp * 3.5)
                cabos["1.5mm²"]["Fase"] += comp_15 * 1.5 # Adiciona margem para retornos
                cabos["1.5mm²"]["Neutro"] += comp_15
                cabos["1.5mm²"]["Terra"] += comp_15

                # --- CÁLCULO TUGs (Tomadas de Uso Geral) ---
                is_molhada = any(x in nome for x in ["cozinha", "banheiro", "serviço", "lavanderia", "copa", "wc"])
                is_banheiro = any(x in nome for x in ["banheiro", "wc", "suíte"])

                if is_banheiro:
                    q_tugs, p_tugs = 1, 600
                else:
                    div = 3.5 if is_molhada else 5.0
                    q_tugs = max(math.ceil(p / div), 1)
                    if is_molhada:
                        p_tugs = (min(q_tugs, 3) * 600) + (max(0, q_tugs - 3) * 100)
                    else:
                        p_tugs = q_tugs * 100
                
                df_calc.at[i, "TUG (Qtd)"] = int(q_tugs)
                df_calc.at[i, "Potência TUG (VA)"] = float(p_tugs)
                pot_tug_total += p_tugs
                
                # Estimativa Cabos 2.5mm² (TUGs)
                comp_25 = p + (q_tugs * 1.5)
                cabos["2.5mm²"]["Fase"] += comp_25
                cabos["2.5mm²"]["Neutro"] += comp_25
                cabos["2.5mm²"]["Terra"] += comp_25

                # --- CÁLCULO TUE (Tomadas de Uso Especial) ---
                tue_w = float(r["TUE (Watts)"])
                if tue_w > 0:
                    v_tue = 220 if (tue_w >= 4000 or tensao_fase == 220) else 127
                    corrente = tue_w / v_tue
                    
                    if corrente <= 21: bitola = "2.5mm²"
                    elif corrente <= 28: bitola = "4.0mm²"
                    elif corrente <= 36: bitola = "6.0mm²"
                    else: bitola = "10.0mm²"
                    
                    disjuntor = "20A" if corrente <= 16 else ("25A" if corrente <= 21 else ("32A" if corrente <= 28 else "40A"))
                    
                    novos_circuitos.append({
                        "Circ": f"C{len(novos_circuitos)+3:02d}", 
                        "Descrição": f"TUE - {r['Cômodo']}",
                        "Potência": f"{tue_w:.0f}W", 
                        "Tensão": f"{v_tue}V", 
                        "Cabo": bitola,
                        "Disjuntor": disjuntor
                    })
                    
                    # Estimativa Cabos TUE
                    comp_tue = (p / 2) + 4.0 # Estimativa até o quadro
                    if v_tue == 220 and tensao_fase == 127:
                        # Bifásico (F + F + T) - Sem neutro para chuveiro bifásico
                        cabos[bitola]["Fase"] += comp_tue * 2
                        cabos[bitola]["Terra"] += comp_tue
                    else:
                        # Monofásico (F + N + T)
                        cabos[bitola]["Fase"] += comp_tue
                        cabos[bitola]["Neutro"] += comp_tue
                        cabos[bitola]["Terra"] += comp_tue

            except Exception as e: 
                print(f"Erro na linha: {e}")
                continue

        # --- CIRCUITOS GERAIS ---
        if pot_ilum_total > 0:
            novos_circuitos.insert(0, {
                "Circ": "C01", "Descrição": "Iluminação Geral", 
                "Potência": f"{pot_ilum_total}VA", "Tensão": f"{tensao_fase}V", 
                "Cabo": "1.5mm²", "Disjuntor": "10A"
            })
        if pot_tug_total > 0:
            novos_circuitos.insert(1, {
                "Circ": "C02", "Descrição": "Tomadas Gerais (TUGs)", 
                "Potência": f"{pot_tug_total}VA", "Tensão": f"{tensao_fase}V", 
                "Cabo": "2.5mm²", "Disjuntor": "20A"
            })
        
        # --- GERAÇÃO DINÂMICA DA LISTA DE MATERIAIS ---
        materiais_dinamicos = []
        
        # 1. Inserir Cabos detalhados (Fase, Neutro, Terra)
        for bitola, vias in cabos.items():
            if vias["Fase"] > 0:
                materiais_dinamicos.append({"Item": f"Cabo Flexível {bitola} (Fase/Retorno)", "Qtd": f"{math.ceil(vias['Fase'])}m"})
            if vias["Neutro"] > 0:
                materiais_dinamicos.append({"Item": f"Cabo Flexível {bitola} (Neutro - Azul)", "Qtd": f"{math.ceil(vias['Neutro'])}m"})
            if vias["Terra"] > 0:
                materiais_dinamicos.append({"Item": f"Cabo Flexível {bitola} (Terra - Verde)", "Qtd": f"{math.ceil(vias['Terra'])}m"})

        # 2. Contar e Inserir Disjuntores do QDC
        contagem_disj = {}
        for c in novos_circuitos:
            dj = c.get("Disjuntor")
            if dj:
                nome_dj = f"Disjuntor DIN Unipolar {dj}" if (c["Tensão"] == "127V" or tensao_fase == 220) else f"Disjuntor DIN Bipolar {dj}"
                contagem_disj[nome_dj] = contagem_disj.get(nome_dj, 0) + 1

        for nome_dj, qtd in contagem_disj.items():
            materiais_dinamicos.append({"Item": nome_dj, "Qtd": f"{qtd} un"})

        # 3. Definir o QDC com espaço reserva (NBR 5410)
        total_circ = len(novos_circuitos)
        tam_qdc = 12 if total_circ <= 6 else (16 if total_circ <= 12 else 24)
        materiais_dinamicos.append({"Item": f"Quadro de Distribuição (QDC) - {tam_qdc} Polos", "Qtd": "1 un"})

        # Salva no estado
        st.session_state.dados_cargas = df_calc
        st.session_state.lista_circuitos = novos_circuitos
        st.session_state.resumo_materiais = materiais_dinamicos
        st.success("✅ Cálculos e materiais gerados com sucesso!")
        st.rerun()

    # 5. QUADROS E PDF
    if st.session_state.lista_circuitos:
        st.divider()
        st.subheader("⚡ Quadro de Circuitos Sugerido (QDC)")
        st.table(pd.DataFrame(st.session_state.lista_circuitos))
        
        st.subheader("📦 Lista Estimada de Materiais")
        st.table(pd.DataFrame(st.session_state.resumo_materiais))

        if st.button("📄 Gerar Memorial Técnico Completo (PDF)", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
                emp = st.session_state.get('nome_empresa', 'VoltSpec Pro')
                reg = st.session_state.get('crt', 'Técnico Responsável')
                
                # Cabeçalho
                pdf.set_fill_color(30, 41, 59); pdf.rect(0, 0, 210, 40, 'F')
                pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 16)
                pdf.cell(190, 10, emp.upper(), ln=True, align="C")
                pdf.set_font("Arial", "", 10); pdf.cell(190, 6, f"Registro: {reg} | Rede: {tensao_fase}V", ln=True, align="C")
                
                # Seção 1: Cargas
                pdf.ln(25); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "1. MEMORIAL DE DIMENSIONAMENTO DE CARGAS", "B", 1, "L")
                pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
                h_c = ["Comodo", "Area", "Iluminacao", "TUGs", "Pot.TUG", "TUE"]
                w_c = [45, 20, 35, 20, 35, 35]
                for h, w in zip(h_c, w_c): pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for _, r in st.session_state.dados_cargas.iterrows():
                    pdf.cell(45, 7, str(r["Cômodo"]), 1)
                    pdf.cell(20, 7, f"{r['Área (m²)']}m2", 1, 0, "C")
                    pdf.cell(35, 7, str(r["Iluminação (VA)"]), 1, 0, "C")
                    pdf.cell(20, 7, str(r["TUG (Qtd)"]), 1, 0, "C")
                    pdf.cell(35, 7, f"{r['Potência TUG (VA)']}VA", 1, 0, "C")
                    pdf.cell(35, 7, f"{r['TUE (Watts)']}W", 1, 1, "C")

                # Seção 2: Quadro de Circuitos
                pdf.ln(10); pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "2. QUADRO DE DISTRIBUIÇÃO (QDC)", "B", 1, "L")
                pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
                h_q = ["Circ.", "Descricao", "Potencia", "Tensao", "Cabo", "Disj."]
                w_q = [15, 65, 30, 25, 30, 25]
                for h, w in zip(h_q, w_q): pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for c in st.session_state.lista_circuitos:
                    pdf.cell(15, 7, c["Circ"], 1, 0, "C")
                    pdf.cell(65, 7, c["Descrição"], 1)
                    pdf.cell(30, 7, c["Potência"], 1, 0, "C")
                    pdf.cell(25, 7, c["Tensão"], 1, 0, "C")
                    pdf.cell(30, 7, c["Cabo"], 1, 0, "C")
                    pdf.cell(25, 7, c["Disjuntor"], 1, 1, "C")

                # Seção 3: Materiais
                pdf.ln(10); pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "3. MATERIAIS SUGERIDOS (ESTIMATIVA INFRAESTRUTURA)", "B", 1, "L")
                pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
                pdf.cell(140, 8, "Item e Especificacao", 1, 0, "C", True); pdf.cell(50, 8, "Qtd", 1, 1, "C", True)
                pdf.set_font("Arial", "", 8)
                for m in st.session_state.resumo_materiais:
                    pdf.cell(140, 7, m["Item"], 1); pdf.cell(50, 7, m["Qtd"], 1, 1, "C")

                pdf_out = pdf.output(dest="S").encode("latin-1", "ignore")
                st.download_button("⬇️ Baixar Projeto Completo (PDF)", pdf_out, "Projeto_Eletrico.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Erro no PDF: {e}")
# --- MÓDULO ORÇAMENTOS (RESTAURADO COMPLETO) ---
elif aba == "💰 Orçamentos":
    st.header("💰 Orçamentos de Serviços")
    cliente = st.text_input("Nome do Cliente:", "Cliente Araxá")
    servicos = [
        {"Descrição": "Ponto de Tomada / Interruptor", "Qtd": 0, "Preço": 85.0},
        {"Descrição": "Ponto de Iluminação", "Qtd": 0, "Preço": 75.0},
        {"Descrição": "Montagem de Quadro (até 12 disj.)", "Qtd": 0, "Preço": 450.0},
        {"Descrição": "Montagem de Quadro (acima 12 disj.)", "Qtd": 0, "Preço": 650.0},
        {"Descrição": "Padrão CEMIG Monofásico", "Qtd": 0, "Preço": 850.0},
        {"Descrição": "Padrão CEMIG Trifásico", "Qtd": 0, "Preço": 1350.0},
        {"Descrição": "Instalação de Chuveiro", "Qtd": 0, "Preço": 110.0},
        {"Descrição": "Laudo de Conformidade", "Qtd": 0, "Preço": 350.0}
    ]
    df_serv = st.data_editor(pd.DataFrame(servicos), num_rows="dynamic", use_container_width=True, key="orc_edt")
    
    total_orc = (df_serv["Qtd"] * df_serv["Preço"]).sum()
    st.subheader(f"Total Serviços: R$ {total_orc:,.2f}")
    
    if st.button("📄 Gerar PDF Orçamento"):
        pdf = gerar_pdf_universal(f"ORCAMENTO - {cliente}", df_serv, [100, 20, 35, 35], ["Descrição", "Qtd", "Unit.", "Subtotal"])
        st.download_button("⬇️ Baixar PDF", pdf, "Orcamento.pdf", "application/pdf")

# --- MÓDULO MATERIAIS (RESTAURADO COMPLETO) ---
elif aba == "📦 Materiais":
    st.header("📦 Lista de Materiais Elétricos")
    materiais = [
        {"Descrição": "Cabo Flexível 2,5mm (Rolo 100m)", "Qtd": 0, "Preço": 285.0},
        {"Descrição": "Cabo Flexível 4,0mm (Rolo 100m)", "Qtd": 0, "Preço": 420.0},
        {"Descrição": "Disjuntor DIN Mono (10A a 32A)", "Qtd": 0, "Preço": 19.90},
        {"Descrição": "Dispositivo DR Bipolar 40A", "Qtd": 0, "Preço": 189.0},
        {"Descrição": "Dispositivo DPS 20kA", "Qtd": 0, "Preço": 58.0},
        {"Descrição": "Caixa de Passagem 4x2", "Qtd": 0, "Preço": 3.50},
        {"Descrição": "Eletroduto Corrugado 3/4 (50m)", "Qtd": 0, "Preço": 75.0}
    ]
    df_mat = st.data_editor(pd.DataFrame(materiais), num_rows="dynamic", use_container_width=True, key="mat_edt")
    
    total_mat = (df_mat["Qtd"] * df_mat["Preço"]).sum()
    st.subheader(f"Total Materiais: R$ {total_mat:,.2f}")
    
    if st.button("📄 Gerar PDF Materiais"):
        pdf = gerar_pdf_universal("LISTA DE MATERIAIS", df_mat, [100, 20, 35, 35], ["Descrição", "Qtd", "Unit.", "Subtotal"])
        st.download_button("⬇️ Baixar PDF", pdf, "Materiais.pdf", "application/pdf")

# --- MÓDULO PRODUTOS (RESTAURADO COMPLETO) ---
elif aba == "🛒 Produtos":
    st.header("🛒 Vitrine de Ferramentas (Mercado Livre)")
    prods = [
        {"nome": "Jogo Chaves Isoladas", "img": "https://http2.mlstatic.com/D_NQ_NP_2X_701755-MLB85959666529_062025-F.webp", "link": "https://meli.la/2xLSiQJ"},
        {"nome": "Alicate Decapador Vonder", "img": "https://http2.mlstatic.com/D_NQ_NP_2X_608489-MLA99480826142_112025-F.webp", "link": "https://meli.la/2L47LTv"},
        {"nome": "Bolsa Ferramentas Reforçada", "img": "https://http2.mlstatic.com/D_NQ_NP_2X_947240-MLA99992405049_112025-F.webp", "link": "https://meli.la/1E4on12"},
        {"nome": "Alicate Crimpar Prensa", "img": "https://http2.mlstatic.com/D_NQ_NP_2X_928036-MLA99440131490_112025-F.webp", "link": "https://meli.la/247XSK7"}
    ]
    
    cols = st.columns(4)
    for i, p in enumerate(prods):
        with cols[i % 4]:
            st.image(p["img"], use_container_width=True)
            st.write(f"**{p['nome']}**")
            st.link_button("🚀 Ver no Mercado Livre", p["link"], use_container_width=True)

# --- MÓDULO DIMENSIONADOR ---

elif aba == "📐 Dimensionador":
    st.header("📐 Cálculo Técnico Profissional (NBR 5410)")
    
    # Cartão de Status da Norma
    status_container = st.container()

    col_inp1, col_inp2, col_inp3 = st.columns(3)
    with col_inp1:
        pot = st.number_input("Potência Total (W):", value=1200.0, step=100.0)
        tipo_carga = st.selectbox("Tipo de Carga:", ["Iluminação", "Tomadas (Geral/TUE)"])
    with col_inp2:
        tensao = st.selectbox("Tensão (V):", [127, 220])
        dist = st.number_input("Distância do Quadro (m):", value=15.0, step=1.0)
    with col_inp3:
        fator_agrup = st.slider("Fator de Agrupamento:", 0.4, 1.0, 1.0, help="0.70 para 3 circuitos no mesmo conduíte")

    # Cálculos de Engenharia
    ib = pot / tensao
    # Ib corrigida pelo fator de agrupamento
    ib_corrigida = ib / fator_agrup
    
    # Lógica de Bitola Mínima NBR 5410
    bitola_minima = 1.5 if tipo_carga == "Iluminação" else 2.5
    
    # Seleção de Bitola por Capacidade de Corrente (Método B1 - Tabela 36)
    if ib_corrigida <= 15.5: bitola_sugerida = 1.5
    elif ib_corrigida <= 21: bitola_sugerida = 2.5
    elif ib_corrigida <= 28: bitola_sugerida = 4.0
    elif ib_corrigida <= 36: bitola_sugerida = 6.0
    else: bitola_sugerida = 10.0

    # Aplica a bitola mínima da norma se a calculada for menor
    bitola_final = max(bitola_sugerida, bitola_minima)
    
    # Cálculo de Queda de Tensão (Resistividade do Cobre = 0.0172)
    # Delta V = (2 * L * I * rho) / S
    queda_v = (2 * dist * ib * 0.0172) / bitola_final
    percentual_queda = (queda_v / tensao) * 100

    # Interface de Resultados
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

    # --- PAINEL DE CONFORMIDADE NBR 5410 ---
    st.subheader("🛡️ Verificação de Conformidade")
    
    erros = []
    avisos = []

    # Verificação 1: Bitola Mínima
    if bitola_sugerida < bitola_minima:
        avisos.append(f"A norma exige mínimo de {bitola_minima}mm² para {tipo_carga.lower()}.")
    
    # Verificação 2: Queda de Tensão (Limite de 4% para circuitos terminais)
    if percentual_queda > 4.0:
        erros.append("Queda de tensão acima de 4% (Limite NBR 5410 para circuitos terminais).")
    
    # Verificação 3: Proteção Sugerida
    disjuntor_sugerido = math.ceil(ib / 5) * 5
    if disjuntor_sugerido < 10: disjuntor_sugerido = 10
    
    # Exibição dos Cards de Status
    if not erros and not avisos:
        st.success("✅ Circuito em conformidade com a NBR 5410.")
    else:
        for erro in erros:
            st.error(f"❌ **CONFORMIDADE:** {erro}")
        for aviso in avisos:
            st.warning(f"⚠️ **OBSERVAÇÃO:** {aviso}")

    with st.expander("📝 Detalhes do Dimensionamento"):
        st.write(f"""
        - **Cabo:** Cobre com isolação em PVC (70°C).
        - **Método de Instalação:** Condutos embutidos em alvenaria (B1).
        - **Resistividade (ρ):** 0.0172 Ω·mm²/m.
        - **Disjuntor Sugerido:** {disjuntor_sugerido}A (Curva B para iluminação, C para motores/TUE).
        """)

# Adicione este bloco dentro da aba "📦 Materiais" para cobrir toda a infraestrutura:
elif aba == "📦 Materiais":
    # ... (código anterior do editor)
    st.info("💡 Dica: Verifique sempre a bitola do cabo no 'Dimensionador' antes de fechar o pedido.")

# --- 8. RODAPÉ E FINALIZAÇÃO DO ARQUIVO ---
st.markdown("---")
c_ft1, c_ft2, c_ft3 = st.columns(3)
with c_ft1:
    st.caption(f"📍 {st.session_state.get('endereco', 'Araxá - MG')}")
with c_ft2:
    st.caption("⚡ Desenvolvido por Spec Pro")
with c_ft3:
    if st.session_state.user:
        st.caption(f"🔑 Logado como: {st.session_state.user.email}")

# --- FIM DO CÓDIGO ---