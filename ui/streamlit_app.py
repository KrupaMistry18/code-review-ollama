import os, requests, streamlit as st
API = os.getenv("REVIEW_API", "http://127.0.0.1:8000/review")

st.set_page_config(page_title="GenAI Code Review (Ollama)", layout="centered")
st.title("GenAI Code Review (Ollama)")
st.caption("Paste a diff or code. Choose focus. Click Review.")

diff = st.text_area("Diff or Code", height=240, placeholder="Paste a unified diff (---/+++/@@) or code…")
focus = st.multiselect("Focus areas", ["security","performance","style"], default=["security","performance","style"])

if st.button("Review", type="primary"):
    if not diff.strip():
        st.warning("Please paste a diff or code.")
    else:
        with st.spinner("Analyzing locally with Ollama…"):
            r = requests.post(API, json={"diff": diff, "focus": focus}, timeout=120)
            if r.ok:
                data = r.json()
                st.subheader("Summary")
                st.write(data.get("summary",""))
                st.subheader("Findings")
                for f in data.get("findings", []):
                    st.markdown(f"- **{f['category'].title()} / {f['severity']}** — {f['message']}")
            else:
                st.error(f"{r.status_code}: {r.text}")
