import streamlit as st
import pandas as pd

st.set_page_config(page_title="Brasil — Liberados x Montados", page_icon="🚚", layout="wide")

# ------------------------------------------------------------------
# Configuração dos estados
# ------------------------------------------------------------------
# Cole aqui a URL publicada em CSV de cada aba HISTORICO_<estado> da planilha.
#
# Como pegar a URL:
# 1. Na planilha Google, Arquivo > Compartilhar > Publicar na Web
# 2. Selecione a aba HISTORICO_<estado> > formato CSV > Publicar
# 3. Copie a URL gerada (algo como .../pubhtml?gid=XXXX&single=true)
# 4. Troque "pubhtml" por "pub" e adicione "&output=csv" no final
CONFIG_ESTADOS = {
    "AM": {
        "nome": "Amazonas",
        "csv_url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vR2XlWGFoKPGlo9p8COnOjenyUrl-gZJC1pdzmzut1BVZFnwY7zJ2_9PRz5CYhHXITswB3JvNohSxkE/pub?gid=119371517&single=true&output=csv",
    },
    "BA": {"nome": "Bahia", "csv_url": ""},
    "DF": {"nome": "Distrito Federal", "csv_url": ""},
    "MG": {"nome": "Minas Gerais", "csv_url": ""},
    "SP": {"nome": "São Paulo", "csv_url": ""},
    "SPW": {"nome": "São Paulo (SPW)", "csv_url": ""},
}


@st.cache_data(ttl=120)
def carregar_historico(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)
    df = df.dropna(subset=["NUMPED", "EXTRACAO_TS"])
    df["EXTRACAO_TS"] = pd.to_datetime(df["EXTRACAO_TS"])
    df["POSICAO"] = df["POSICAO"].astype(str).str.strip().str.upper()
    df["NUMPED"] = df["NUMPED"].astype(str)
    return df


def formatar_ts(ts: pd.Timestamp) -> str:
    return ts.strftime("%d/%m/%Y %H:%M")


# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("🚚 Brasil — Liberados x Montados")
st.caption("Acompanhamento de pedidos liberados e montados por estado, com histórico de extrações e horário de corte.")

col_estado, _ = st.columns([1, 3])
with col_estado:
    sigla = st.selectbox(
        "Estado",
        options=list(CONFIG_ESTADOS.keys()),
        format_func=lambda s: f"{s} — {CONFIG_ESTADOS[s]['nome']}",
    )

info = CONFIG_ESTADOS[sigla]
if not info["csv_url"]:
    st.warning(f"Nenhuma URL configurada para **{sigla}** ainda. Edite `CONFIG_ESTADOS` no topo do arquivo.")
    st.stop()

try:
    with st.spinner(f"Carregando dados de {sigla}..."):
        df = carregar_historico(info["csv_url"])
except Exception as e:
    st.error(f"Erro ao carregar dados de {sigla}: {e}")
    st.stop()

snapshots = sorted(df["EXTRACAO_TS"].unique())
if not snapshots:
    st.warning("Nenhum snapshot encontrado. Rode o snapshot na planilha primeiro.")
    st.stop()

st.success(f"{len(df)} linhas carregadas · {len(snapshots)} snapshot(s) disponível(is) para {sigla}.")

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