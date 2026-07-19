import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brasil — Liberados x Montados", page_icon="🚚", layout="wide")

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------
# ID da planilha: é o trecho entre /d/ e /edit na URL da sua planilha.
# Ex: https://docs.google.com/spreadsheets/d/AQUI_ESTA_O_ID/edit -> copie AQUI_ESTA_O_ID
SPREADSHEET_ID = "1NnTPvTdSZKJfPxiSA5R3bgpL2SzQAeQf2vNTvoKFMC4"

# Nome da aba de histórico de cada estado (criadas automaticamente pelo Apps Script)
CONFIG_ESTADOS = {
    "AM": {"nome": "Amazonas", "aba": "HISTORICO_AM"},
    "BA": {"nome": "Bahia", "aba": "HISTORICO_BA"},
    "DF": {"nome": "Distrito Federal", "aba": "HISTORICO_DF"},
    "MG": {"nome": "Minas Gerais", "aba": "HISTORICO_MG"},
    "SP": {"nome": "São Paulo", "aba": "HISTORICO_SP"},
    "SPW": {"nome": "São Paulo (SPW)", "aba": "HISTORICO_SPW"},
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@st.cache_resource
def conectar_planilha():
    credenciais = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    cliente = gspread.authorize(credenciais)
    return cliente.open_by_key(SPREADSHEET_ID)


@st.cache_data(ttl=30)
def carregar_historico(aba_nome: str) -> pd.DataFrame:
    planilha = conectar_planilha()
    aba = planilha.worksheet(aba_nome)
    registros = aba.get_all_records()
    df = pd.DataFrame(registros)

    if df.empty:
        return df

    df = df.dropna(subset=["NUMPED", "EXTRACAO_TS"])
    df["EXTRACAO_TS"] = pd.to_datetime(df["EXTRACAO_TS"])
    df["POSICAO"] = df["POSICAO"].astype(str).str.strip().str.upper()
    df["NUMPED"] = df["NUMPED"].astype(str)
    # O export do Whyntor traz uma linha por item/produto do pedido, então o
    # mesmo NUMPED pode se repetir várias vezes dentro do mesmo snapshot.
    # Para contar pedidos (não itens), mantemos só uma linha por NUMPED em
    # cada extração.
    df = df.drop_duplicates(subset=["EXTRACAO_TS", "NUMPED"], keep="first")
    return df


def formatar_ts(ts: pd.Timestamp) -> str:
    return ts.strftime("%d/%m/%Y %H:%M")


# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("🚚 Brasil — Liberados x Montados")
st.caption("Acompanhamento de pedidos liberados e montados por estado, com histórico de extrações e horário de corte. Conectado ao vivo com a planilha.")

col_estado, col_atualizar = st.columns([3, 1])
with col_estado:
    sigla = st.selectbox(
        "Estado",
        options=list(CONFIG_ESTADOS.keys()),
        format_func=lambda s: f"{s} — {CONFIG_ESTADOS[s]['nome']}",
    )
with col_atualizar:
    st.write("")
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()

info = CONFIG_ESTADOS[sigla]

if SPREADSHEET_ID == "COLE_AQUI_O_ID_DA_PLANILHA":
    st.error("Configure o SPREADSHEET_ID no topo do arquivo `streamlit_app.py`.")
    st.stop()

try:
    with st.spinner(f"Carregando dados de {sigla}..."):
        df = carregar_historico(info["aba"])
except gspread.exceptions.WorksheetNotFound:
    st.warning(f"A aba **{info['aba']}** ainda não existe na planilha. Rode um snapshot desse estado primeiro.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar dados de {sigla} ({type(e).__name__}):")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning(f"A aba {info['aba']} está vazia. Rode um snapshot desse estado primeiro.")
    st.stop()

snapshots = sorted(df["EXTRACAO_TS"].unique())

st.success(f"{len(df)} pedidos carregados · {len(snapshots)} snapshot(s) disponível(is) para {sigla}. Atualiza sozinho a cada 30s.")

# ------------------------------------------------------------------
# Seção 1: situação em um snapshot (o "corte")
# ------------------------------------------------------------------
st.header("📍 Situação em um snapshot")

ts_corte = st.selectbox(
    "Extração (corte)",
    options=snapshots,
    index=len(snapshots) - 1,
    format_func=formatar_ts,
)

df_corte = df[df["EXTRACAO_TS"] == ts_corte]
liberados = df_corte[df_corte["POSICAO"] == "L"]
montados = df_corte[df_corte["POSICAO"] == "M"]

c1, c2, c3 = st.columns(3)
c1.metric("Liberados (L)", len(liberados))
c2.metric("Montados (M)", len(montados))
c3.metric("Total no snapshot", len(df_corte))

with st.expander("Ver pedidos deste snapshot"):
    st.dataframe(
        df_corte[["NUMPED", "NOMECLIENTE", "POSICAO", "PRACA", "DESTINO"]],
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------------
# Seção 2: comparar dois momentos
# ------------------------------------------------------------------
st.header("🔀 Comparar dois momentos")

if len(snapshots) < 2:
    st.info("Você precisa de pelo menos 2 snapshots para comparar. Rode o snapshot na planilha novamente mais tarde.")
else:
    col_a, col_b = st.columns(2)
    with col_a:
        ts_antes = st.selectbox("Antes", options=snapshots, index=0, format_func=formatar_ts, key="antes")
    with col_b:
        ts_depois = st.selectbox("Depois", options=snapshots, index=len(snapshots) - 1, format_func=formatar_ts, key="depois")

    if ts_antes == ts_depois:
        st.warning("Escolha dois snapshots diferentes para comparar.")
    else:
        df_antes = df[df["EXTRACAO_TS"] == ts_antes].set_index("NUMPED")
        df_depois = df[df["EXTRACAO_TS"] == ts_depois].set_index("NUMPED")

        numped_antes = set(df_antes.index)
        numped_depois = set(df_depois.index)

        cancelados_ids = numped_antes - numped_depois
        novos_ids = numped_depois - numped_antes
        comuns_ids = numped_antes & numped_depois

        transicao_lm_ids = [
            n for n in comuns_ids
            if df_antes.loc[n, "POSICAO"] == "L" and df_depois.loc[n, "POSICAO"] == "M"
        ]
        permanece_l_ids = [
            n for n in comuns_ids
            if df_antes.loc[n, "POSICAO"] == "L" and df_depois.loc[n, "POSICAO"] == "L"
        ]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Saíram de L → M", len(transicao_lm_ids))
        c2.metric("Continuam em L", len(permanece_l_ids))
        c3.metric("Cancelados (sumiram)", len(cancelados_ids))
        c4.metric("Novos pedidos", len(novos_ids))

        tab1, tab2 = st.tabs(["Cancelados", "Saíram de L → M"])
        with tab1:
            st.dataframe(
                df_antes.loc[list(cancelados_ids), ["NOMECLIENTE", "POSICAO", "PRACA"]].reset_index()
                if cancelados_ids else pd.DataFrame(columns=["NUMPED", "NOMECLIENTE", "POSICAO", "PRACA"]),
                use_container_width=True,
                hide_index=True,
            )
        with tab2:
            st.dataframe(
                df_depois.loc[transicao_lm_ids, ["NOMECLIENTE", "PRACA", "DESTINO"]].reset_index()
                if transicao_lm_ids else pd.DataFrame(columns=["NUMPED", "NOMECLIENTE", "PRACA", "DESTINO"]),
                use_container_width=True,
                hide_index=True,
            )
