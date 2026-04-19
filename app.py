import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Universal", layout="wide")

st.title("🏦 Extrator Bancário Padronizado (Fair Value)")
st.markdown("Converta qualquer extrato para o modelo de **4 colunas padrão**.")

# 1. Upload do Arquivo
arquivo_pdf = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    # Abrindo o PDF enviado
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Limpa espaços e une textos (evita nomes cortados no Sicoob)
                    linha_limpa = [" ".join(str(c).split()) if c else "" for c in linha]
                    if any(linha_limpa): 
                        dados_brutos.append(linha_limpa)

    df_b = pd.DataFrame(dados_brutos)

    st.subheader("📋 Passo 2: Calibração de Colunas")
    st.write("Identifique as colunas na prévia do seu arquivo abaixo:")
    st.dataframe(df_b.head(15))

    col1, col2, col3 = st.columns(3)
    with col1: c_data = st.number_input("Nº coluna DATA", min_value=0, value=0)
    with col2: c_desc = st.number_input("Nº coluna HISTÓRICO", min_value=0, value=2)
    with col3: c_valor = st.number_input("Nº coluna VALOR", min_value=0, value=3)

    if st.button("Gerar Movimentação Líquida"):
        # Mapeamento inicial
        df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
        df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

        # --- REGRAS DE OURO DA FAIR VALUE ---
        # 1. Remover Saldos e Cabeçalhos Repetidos
        termos_ignorar = ["SALDO DO DIA", "SALDO ANTERIOR", "SALDO FINAL", "SALDO DISPONÍVEL", "DATA", "HISTÓRICO"]
        df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_ignorar), na=False)]
        df_f = df_f[df_f['DATA'].str.upper() != "DATA"]

        # 2. Identificação Universal de Sinais (C, D, -, +)
        def processar_valor(v):
            v_str = str(v).upper()
            sinal = "C" # Padrão crédito
            if 'D' in v_str or '-' in v_str:
                sinal = "D"
            
            # Limpa tudo que não for número ou separador
            num_limpo = re.sub(r'[^\d,.]', '', v_str)
            return pd.Series([num_limpo, sinal])

        df_f[['VALOR', 'SINAL']] = df_f['VALOR_BRUTO'].apply(processar_valor)

        # Criando o CSV de 4 colunas padrão
        df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'SINAL']].reset_index(drop=True)

        st.subheader("✅ CSV Padronizado Gerado")
        st.dataframe(df_final)

        # Passo 5: Download
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar CSV da Fair Value", csv, "extrato_padronizado.csv", "text/csv")
