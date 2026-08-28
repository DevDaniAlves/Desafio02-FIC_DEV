"""Interface Streamlit mínima."""
import requests
import streamlit as st

st.set_page_config(page_title="Consulta de atendimentos",page_icon="🔎")
st.title("Consulta inteligente de atendimentos")
question=st.text_area("Pergunta",placeholder="Quais problemas de instalação do Python aparecem com maior frequência?")
top_k=st.slider("Quantidade de fontes",1,10,5)
if st.button("Consultar",type="primary",disabled=not question.strip()):
    try:
        response=requests.post("http://127.0.0.1:8000/ask",json={"pergunta":question,"top_k":top_k},timeout=60); response.raise_for_status(); data=response.json()
        st.subheader("Resposta"); st.write(data["resposta"]); st.caption(f"Modo: {data.get('modo')}")
        st.subheader("Fontes")
        for source in data.get("fontes",[]): st.markdown(f"**{source.get('protocolo')}** - {source.get('documento')}, página {source.get('pagina')} - similaridade {source.get('similaridade')}")
    except requests.RequestException as exc: st.error(f"Não foi possível consultar a API: {exc}")
