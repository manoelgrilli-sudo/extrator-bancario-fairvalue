import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Pro", layout="wide")

st.title("🏦 Extrator Fair Value: Validação e Padronização")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Converte tudo para string e limpa None
                    linha_limpa = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    if any(linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        # ---------------------------------------------------------
        # 1. PRÉVIA REAL (O "PRINT" DO CABEÇALHO)
        # ---------------------------------------------------------
        st.subheader("🔍 1. Prévia do Extrato (Cabeçalho Original)")
        st.info("Identifique abaixo os números das colunas para configurar o extrator.")
        st.dataframe(df_b.head(50), use_container_width=True)

        st.markdown("### ⚙️ 2. Calibração de Colunas")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº da coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº da coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº da coluna de VALOR", min_value=0, value=3)

        if st.button("🚀 VALIDAR E GERAR MOVIMENTAÇÃO LÍQUIDA"):
            try:
                # Criando a estrutura baseada na sua seleção
                linhas_processadas = []
                
                # Percorre o dataframe para "soldar" linhas quebradas (comum no Sicoob)
                for i in range(len(df_b)):
                    data = df_b.iloc[i, c_data]
                    hist = df_b.iloc[i, c_desc]
                    valor = df_b.iloc[i, c_valor]
                    
                    # Se a linha atual não tem data mas tem histórico/valor, 
                    # ela pertence à linha de cima (ajuste para o Sicoob)
                    if data == "" and i > 0:
                        if len(linhas_processadas) > 0:
                            linhas_processadas[-1][1] += " " + hist
                            if valor != "": linhas_processadas[-1][2] = valor
                        continue
                    
                    linhas_processadas.append([data, hist, valor])

                df_f = pd.DataFrame(linhas_processadas, columns=['DATA', 'HISTORICO', 'VALOR_BRUTO'])

                # ---------------------------------------------------------
                # 2. EXCLUIR SALDOS (ANTERIOR, DIA, FINAL)
                # ---------------------------------------------------------
                termos_ignorar = ["SALDO", "RESUMO", "DATA", "HISTÓRICO", "VALOR", "DOCUMENTO", "CHEQUE ESPECIAL", "TARIFAS VENCIDAS"]
                df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_ignorar), na=False)]
                df_f = df_f[df_f['DATA'].str.strip() != ""]

                # ---------------------------------------------------------
                # 3. COLUNA INDICATIVO (C/D) E VALOR LIMPO
                # ---------------------------------------------------------
                def separar_sinal(texto_valor):
                    v = str(texto_valor).upper().strip()
                    # Identifica D se houver sinal de menos (-) ou a letra D
                    indicativo = "D" if "-" in v or "D" in v else "C"
                    # Remove tudo que não é número, vírgula ou ponto
                    valor_limpo = re.sub(r'[^\d,.]', '', v)
                    return pd.Series([valor_limpo, indicativo])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(separar_sinal)

                # Finalizando a tabela
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success(f"✅ Sucesso! {len(df_final)} movimentações líquidas processadas.")
                st.dataframe(df_final, use_container_width=True)

                # Download
                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Fair Value", csv, "extrato_padronizado.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
