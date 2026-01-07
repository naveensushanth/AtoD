import streamlit as st
from PIL import Image
import io
import json
from diagram_analyzer import DiagramAnalyzer
from terraform_generator import TerraformGenerator

# ---------------------------------------------------------
# Page Config
# ---------------------------------------------------------
st.set_page_config(
    page_title="Azure Architecture Analyzer (Interactive)",
    page_icon="☁️",
    layout="wide"
)

# ---------------------------------------------------------
# Session State
# ---------------------------------------------------------
def init_state():
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "resource_decisions" not in st.session_state:
        st.session_state.resource_decisions = {}
    if "resource_configs" not in st.session_state:
        st.session_state.resource_configs = {}
    if "terraform_code" not in st.session_state:
        st.session_state.terraform_code = None

init_state()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("## ☁️ Azure Architecture Diagram → Interactive Terraform")

# ---------------------------------------------------------
# Sidebar – Azure OpenAI Config
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔐 Azure OpenAI Configuration")

    api_key = st.text_input("API Key", type="password")
    azure_endpoint = st.text_input("Azure OpenAI Endpoint")
    deployment_name = st.text_input("Deployment Name", value="gpt-4o")
    api_version = st.selectbox(
        "API Version",
        ["2024-02-15-preview", "2023-12-01-preview"]
    )

# ---------------------------------------------------------
# Upload Diagram
# ---------------------------------------------------------
st.header("📤 Upload Architecture Diagram")
uploaded_file = st.file_uploader("Upload PNG / JPG", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Architecture Diagram", use_container_width=True)

    # -----------------------------------------------------
    # Analyze Diagram
    # -----------------------------------------------------
    if st.button("🔍 Analyze Diagram"):
        if not api_key or not azure_endpoint or not deployment_name:
            st.error("Please configure Azure OpenAI details")
        else:
            with st.spinner("Analyzing diagram..."):
                analyzer = DiagramAnalyzer(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    deployment_name=deployment_name,
                    api_version=api_version
                )
                st.session_state.analysis_result = analyzer.analyze_diagram(image)

# ---------------------------------------------------------
# Analysis Result
# ---------------------------------------------------------
if st.session_state.analysis_result and st.session_state.analysis_result.get("metadata", {}).get("success"):

    result = st.session_state.analysis_result
    resources = result.get("resources", [])

    st.markdown("---")
    st.header("🧩 Resource Selection & Configuration")

    # -----------------------------------------------------
    # Interactive Resource Configuration
    # -----------------------------------------------------
    for idx, resource in enumerate(resources):
        resource_id = f"{resource['resource_type']}_{idx}"

        with st.expander(f"🔹 {resource['resource_name']} ({resource['resource_type']})"):

            deploy = st.radio(
                "Do you want to deploy this resource?",
                ["Yes", "No"],
                horizontal=True,
                key=f"deploy_{resource_id}"
            )

            st.session_state.resource_decisions[resource_id] = deploy

            if deploy == "Yes":
                col1, col2 = st.columns(2)

                with col1:
                    rg_name = st.text_input(
                        "Resource Group Name",
                        value="rg-platform-core",
                        key=f"rg_{resource_id}"
                    )

                    region = st.selectbox(
                        "Region",
                        ["Central India", "East US", "West Europe"],
                        key=f"region_{resource_id}"
                    )

                with col2:
                    sku = st.text_input(
                        "SKU / Tier",
                        value="Standard",
                        key=f"sku_{resource_id}"
                    )

                    public_access = st.selectbox(
                        "Public Access",
                        ["Disabled", "Enabled"],
                        key=f"public_{resource_id}"
                    )

                st.session_state.resource_configs[resource_id] = {
                    "resource_name": resource["resource_name"],
                    "resource_type": resource["resource_type"],
                    "category": resource["category"],
                    "rg_name": rg_name,
                    "region": region,
                    "sku": sku,
                    "public_access": public_access == "Enabled"
                }

    # -----------------------------------------------------
    # Generate Terraform
    # -----------------------------------------------------
    st.markdown("---")
    if st.button("🚀 Generate Terraform"):

        approved_resources = [
            cfg for rid, cfg in st.session_state.resource_configs.items()
            if st.session_state.resource_decisions.get(rid) == "Yes"
        ]

        if not approved_resources:
            st.warning("No resources selected for deployment")
        else:
            filtered_result = {
                **result,
                "resources": approved_resources
            }

            tf_generator = TerraformGenerator(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                deployment_name=deployment_name,
                api_version=api_version
            )

            with st.spinner("Generating Terraform code..."):
                st.session_state.terraform_code = tf_generator.generate_terraform(
                    filtered_result,
                    region="Central India"
                )

# ---------------------------------------------------------
# Terraform Output
# ---------------------------------------------------------
if st.session_state.terraform_code:
    st.markdown("---")
    st.header("🧱 Generated Terraform")

    tab1, tab2, tab3 = st.tabs(["main.tf", "variables.tf", "outputs.tf"])

    with tab1:
        st.code(st.session_state.terraform_code.get("main_tf", ""), language="hcl")

    with tab2:
        st.code(st.session_state.terraform_code.get("variables_tf", ""), language="hcl")

    with tab3:
        st.code(st.session_state.terraform_code.get("outputs_tf", ""), language="hcl")
