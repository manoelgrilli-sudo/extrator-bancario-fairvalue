import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Pro", layout="wide")

st.title("🏦 Extrator Fair Value: Validação e Padronização")

# 1. Upload
arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Limpa espaços e trata como texto
                    linha_limpa = [" ".join(str(c).split()) if c else "" for c in linha]
                    if any(c.strip() for c in linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        # ---------------------------------------------------------
        # 1. APRESENTAR PRÉVIA (O "PRINT" DO CABEÇALHO)
        # ---------------------------------------------------------
        st.subheader("🔍 Verificação do Cabeçalho")
        st.warning("⚠️ Verifique abaixo quais colunas correspondem a Data, Histórico e Valor no extrato original.")
        st.dataframe(df_b.head(20), use_container_width=True)

        st.markdown("### ⚙️ Calibração de Colunas")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº da coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº da coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº da coluna de VALOR", min_value=0, value=3)

        # O sistema só avança se o operador clicar aqui
        if st.button("🚀 VALIDAR E GERAR MOVIMENTAÇÃO LÍQUIDA"):
            try:
                # Mapeia as colunas escolhidas
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_ORIGINAL']
                
                # Força formato texto
                df_f = df_f.astype(str)

                # ---------------------------------------------------------
                # 2. EXCLUIR SALDOS (ANTERIOR, DIA, FINAL)
                # ---------------------------------------------------------
                termos_excluir = ["SALDO", "RESUMO", "DATA", "HISTÓRICO", "DOCUMENTO", "TOTAL"]
                df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_excluir), na=False)]
                df_f = df_f[df_f['DATA'].str.strip() != ""]

                # ---------------------------------------------------------
                # 3. CRIAR COLUNA INDICATIVO (C/D) E LIMPAR VALOR
                # ---------------------------------------------------------
                def identificar_sinal_e_limpar(valor_bruto):
                    v = valor_bruto.upper().strip()
                    # Identifica sinal
                    sinal = "C" # Padrão crédito
                    if "D" in v or "-" in v:
                        sinal = "D"
                    
                    # Limpa o valor (remove R$, letras, sinais, mantendo apenas números e pontuação)
                    num_limpo = re.sub(r'[^\d,.]', '', v)
                    return pd.Series([num_limpo, sinal])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_ORIGINAL'].apply(identificar_sinal_e_limpar)

                # Resultado Final Padronizado
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success(f"✅ Processado! {len(df_final)} movimentações líquidas identificadas.")
                st.dataframe(df_final, use_container_width=True)

                # Exportação
                csv = df_final.to_csv(index=False, sep=';', encoding='latin1').encode('latin1')
                st.download_button("📥 Baixar CSV Fair Value", csv, "extrato_limpo.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro na calibração: {e}. Verifique se os números das colunas estão corretos na prévia.")
    else:
        st.error("Não conseguimos ler os dados deste PDF. Verifique se ele é um extrato original.")
