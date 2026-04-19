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
            # Extraímos o texto puro e as tabelas para não perder nada
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Filtramos apenas linhas que têm conteúdo real
                    linha_limpa = [" ".join(str(c).split()) if c else "" for c in linha]
                    if any(c.strip() for c in linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        # ---------------------------------------------------------
        # 1. PRÉVIA REAL (MOSTRANDO AS MOVIMENTAÇÕES)
        # ---------------------------------------------------------
        st.subheader("🔍 Verificação do Cabeçalho e Dados")
        st.info("👆 Role a tabela abaixo para confirmar se os nomes dos clientes e valores estão aparecendo.")
        
        # Mostramos 50 linhas para garantir que o operador veja os dados reais
        st.dataframe(df_b.head(50), use_container_width=True)

        st.markdown("### ⚙️ Calibração de Colunas")
        st.write("Identifique na tabela acima os números das colunas:")
        
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº da coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº da coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº da coluna de VALOR", min_value=0, value=3)

        if st.button("🚀 VALIDAR E GERAR MOVIMENTAÇÃO LÍQUIDA"):
            try:
                # Mapeamento
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']
                df_f = df_f.astype(str)

                # ---------------------------------------------------------
                # 2. EXCLUSÃO DE SALDOS (Lógica Abrangente)
                # ---------------------------------------------------------
                # Remove linhas de saldo e títulos repetidos
                termos_ignorar = ["SALDO DO DIA", "SALDO ANTERIOR", "SALDO FINAL", "SALDO DISPONÍVEL", "RESUMO", "DATA", "HISTÓRICO", "VALOR"]
                df_f = df_f[~df_f['HISTORICO'].str.upper().str.contains('|'.join(termos_ignorar), na=False)]
                
                # Remove linhas onde a data está vazia ou é apenas o título
                df_f = df_f[df_f['DATA'].str.strip() != ""]
                df_f = df_f[df_f['DATA'].str.upper() != "DATA"]

                # ---------------------------------------------------------
                # 3. COLUNA INDICATIVO (D/C) E LIMPEZA DE VALOR
                # ---------------------------------------------------------
                def tratar_valor_e_sinal(texto_valor):
                    v = texto_valor.upper().strip()
                    sinal = "C" # Crédito por padrão
                    
                    # Checa se tem sinal de menos ou a letra D
                    if "-" in v or "D" in v:
                        sinal = "D"
                    
                    # Limpa o valor: mantém apenas números, vírgula e ponto
                    valor_limpo = re.sub(r'[^\d,.]', '', v)
                    return pd.Series([valor_limpo, sinal])

                # Aplica a lógica em massa
                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(tratar_valor_e_sinal)

                # Filtro final: remove linhas que ficaram sem valor após a limpeza
                df_f = df_f[df_f['VALOR'] != ""]

                # Exibição do Resultado Final
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success(f"✅ Sucesso! {len(df_final)} movimentações líquidas processadas.")
                st.dataframe(df_final, use_container_width=True)

                # Exportação CSV
                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Fair Value", csv, "extrato_padronizado.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro ao processar as colunas: {e}")
