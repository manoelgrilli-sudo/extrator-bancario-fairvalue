import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Total", layout="wide")

st.title("🏦 Extrator Fair Value: Extração Integral")
st.markdown("Este modelo extrai todas as linhas do extrato para garantir que nenhuma informação seja perdida.")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Converte tudo para texto, mantendo o conteúdo original integralmente
                    linha_limpa = [str(c).strip() if c is not None else "" for c in linha]
                    if any(linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        # ---------------------------------------------------------
        # 1. PRÉVIA DO EXTRATO (O PRINT PARA CALIBRAÇÃO)
        # ---------------------------------------------------------
        st.subheader("🔍 1. Print do Extrato Original")
        st.info("Observe a tabela abaixo e indique os números das colunas.")
        st.dataframe(df_b.head(100), use_container_width=True)

        st.markdown("### ⚙️ 2. Calibração")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº coluna de VALOR", min_value=0, value=3)

        if st.button("🚀 PROCESSAR EXTRATO COMPLETO"):
            try:
                # Extração sem filtros de exclusão
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']
                
                # ---------------------------------------------------------
                # 3. LÓGICA DE INDICATIVO (C/D) E LIMPEZA DE VALOR
                # ---------------------------------------------------------
                def tratar_financeiro(v_bruto):
                    texto = str(v_bruto).upper()
                    # Se não houver nada na célula de valor, retorna vazio
                    if not texto.strip():
                        return pd.Series(["", ""])
                    
                    # Identifica D se houver sinal de menos (-) ou a letra D
                    indicativo = "D" if "-" in texto or "D" in texto else "C"
                    
                    # Limpa o valor mantendo apenas números e separadores decimais
                    valor_num = re.sub(r'[^\d,.]', '', texto)
                    return pd.Series([valor_num, indicativo])

                # Aplica a separação de valor e indicativo
                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(tratar_financeiro)

                # Mantemos apenas as 4 colunas desejadas, mas com TODAS as linhas
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success("✅ Extração integral concluída!")
                st.dataframe(df_final, use_container_width=True)

                # Exportação
                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Completo", csv, "extrato_integra_fairvalue.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro ao processar: {e}")
