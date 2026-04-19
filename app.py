import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Universal", layout="wide")

st.title("🏦 Extrator Bancário Padronizado (Fair Value)")
st.markdown("Transforme extratos complexos em um modelo limpo de **4 colunas**.")

arquivo_pdf = st.file_uploader("🚀 Passo 1: Arraste seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            # Extração de texto por linhas para garantir que nada escape
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Une textos e remove quebras de linha
                    linha_limpa = [" ".join(str(c).split()) if c else "" for c in linha]
                    # Só adiciona se a linha tiver pelo menos uma informação
                    if any(c.strip() for c in linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        st.markdown("---")
        st.subheader("📋 Passo 2: Calibração Visual")
        st.info("💡 Observe os dados abaixo. Se a primeira linha for apenas o título, procure os dados reais logo abaixo.")
        
        # Mostramos 30 linhas para garantir que os dados apareçam após o cabeçalho
        st.dataframe(df_b.head(30), use_container_width=True)

        st.write("🎯 **Informe os números das colunas baseados na tabela acima:**")
        
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº Coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº Coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº Coluna de VALOR", min_value=0, value=3)

        if st.button("✨ Gerar Movimentação Líquida"):
            # Filtra apenas colunas existentes para evitar erro de índice
            try:
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

                # --- LIMPEZA CIRÚRGICA ATUALIZADA ---
                # Remove apenas se a célula for EXATAMENTE "Data" ou "Histórico"
                df_f = df_f[df_f['DATA'].str.strip().upper() != "DATA"]
                df_f = df_f[df_f['HISTORICO'].str.strip().upper() != "HISTÓRICO"]
                
                # Remove linhas de saldo que não são movimentação líquida [cite: 11, 15]
                termos_saldo = ["SALDO DO DIA", "SALDO ANTERIOR", "SALDO FINAL", "RESUMO"]
                df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_saldo), na=False)]
                
                # Remove linhas totalmente vazias
                df_f = df_f.dropna(subset=['DATA', 'VALOR_BRUTO'], how='all')

                # Identificação de Sinal
                def extrair_sinal(v):
                    v_str = str(v).upper()
                    return "D" if 'D' in v_str or '-' in v_str else "C"

                def extrair_valor(v):
                    v_str = str(v).upper()
                    return re.sub(r'[^\d,.]', '', v_str)

                df_f['SINAL'] = df_f['VALOR_BRUTO'].apply(extrair_sinal)
                df_f['VALOR'] = df_f['VALOR_BRUTO'].apply(extrair_valor)

                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'SINAL']].reset_index(drop=True)

                if not df_final.empty:
                    st.success(f"✅ Sucesso! {len(df_final)} movimentações encontradas.")
                    st.dataframe(df_final, use_container_width=True)
                    csv = df_final.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar CSV Padronizado", csv, "extrato_fairvalue.csv", "text/csv")
                else:
                    st.warning("⚠️ Nenhuma movimentação líquida encontrada. Verifique se as colunas estão corretas.")
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
    else:
        st.error("Não foi possível encontrar tabelas neste PDF.")
