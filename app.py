import streamlit as st
import Legobuilder
st.markdown("""
<style>
    body {
        background-color: #fff3e0;
    }
    .stApp {
        background: linear-gradient(to bottom, #ffeb3b, #ff7043);
    }
    h1, h2, h3 {
        color: #d32f2f;
    }
    .stButton>button {
        background-color: #d32f2f;
        color: white;
        border-radius: 12px;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="LEGO Build Generator", page_icon="🧱", layout="centered")

st.markdown("""
<style>
    .main {
        background-color: #f7f7f7;
    }
    h1 {
        color: #ff6a00;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🧱 LEGO Alternate Build Generator")
st.markdown("Turn your LEGO set into a new custom build using AI.")
st.info("🔎 Want to see how the parts look? Visit BrickLink and search your set number to see clear images of every piece and color.")
st.warning(
        "This build is a conceptual guide. Some connections may require creative adjustment, "
        "as the AI cannot fully simulate LEGO physics."
    )



set_number = st.text_input("Enter LEGO set number:")

if set_number:
    set_number = Legobuilder.normalize_set_number(set_number)
    inventory = Legobuilder.build_inventory(set_number)

    if not inventory:
        st.error("Could not load set data.")
    else:
        st.success(f"Total parts: {inventory['total_parts']}")
       

    size = st.selectbox("Choose build size:", ["small", "medium", "large"])
    build_type = st.text_input("Choose build type (vehicle, robot, structure, etc.):")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 Generate Build"):

    selected_parts = Legobuilder.select_build_parts(inventory, size)

    if not selected_parts:
        st.error("This set is too small for the selected build size.")
        st.stop()

    st.subheader("Selected Parts")
    for part, qty in selected_parts.items():
        st.write(f"- {part}: {qty}")

    build = Legobuilder.generate_build_description(build_type, selected_parts, size)

    st.subheader("Build Instructions")
    st.text(build)


    guidance = Legobuilder.generate_ai_guidance(
        build, inventory, Legobuilder.extract_constraints(inventory)
    )

    st.subheader("AI Guidance")
    for g in guidance:
        st.write(g)


