import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Configuração da Página
st.set_page_config(page_title="Fair Value - Extrator Universal", layout="wide")

st.title("🏦 Extrator Bancário Padronizado (Fair Value)")
st.markdown("Transforme extratos complexos em um modelo limpo de **4 colunas**.")

# 1. Upload do Arquivo
arquivo_pdf = st.file_uploader("🚀 Passo 1: Arraste seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Une textos e limpa quebras de linha (essencial para Sicoob)
                    linha_limpa = [" ".join(str(c).split()) if c else "" for c in linha]
                    if any(linha_limpa): 
                        dados_brutos.append(linha_limpa)

    df_b = pd.DataFrame(dados_brutos)

    # --- NOVIDADE: PRÉVIA VISUAL PARA CALIBRAÇÃO ---
    st.markdown("---")
    st.subheader("📋 Passo 2: Calibração Visual")
    st.info("💡 **Como fazer:** Observe os títulos e dados abaixo. Identifique o número da coluna para Data, Histórico e Valor.")
    
    # Exibe a prévia com destaque
    st.dataframe(df_b.head(15), use_container_width=True)

    st.write("🎯 **Informe os números das colunas baseados na tabela acima:**")
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        c_data = st.number_input("Nº Coluna de DATA", min_value=0, value=0)
    with col2: 
        c_desc = st.number_input("Nº Coluna de HISTÓRICO", min_value=0, value=2)
    with col3: 
        c_valor = st.number_input("Nº Coluna de VALOR", min_value=0, value=3)

    if st.button("✨ Gerar Movimentação Líquida"):
        # Mapeamento
        df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
        df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

        # Regras de Limpeza (Ignorar Saldos e Lixo)
        termos_ignorar = ["SALDO", "DATA", "HISTÓRICO", "RESUMO", "TOTAL", "EXTRATO"]
        df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_ignorar), na=False)]
        df_f = df_f[df_f['DATA'].str.strip() != ""]

        # Lógica de Sinal e Valor
        def extrair_sinal(v):
            v_str = str(v).upper()
            return "D" if 'D' in v_str or '-' in v_str else "C"

        def extrair_valor(v):
            v_str = str(v).upper()
            return re.sub(r'[^\d,.]', '', v_str)

        df_f['SINAL'] = df_f['VALOR_BRUTO'].apply(extrair_sinal)
        df_f['VALOR'] = df_f['VALOR_BRUTO'].apply(extrair_valor)

        # Modelo Padrão de 4 Colunas
        df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'SINAL']].reset_index(drop=True)

        st.success("✅ Processamento concluído com sucesso!")
        st.dataframe(df_final, use_container_width=True)

        # Download do CSV
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar CSV Padronizado", csv, "extrato_fairvalue.csv", "text/csv")
