"""
Azure Architecture Diagram Analyzer - Enhanced with Terraform & Cost Estimation
Modified for Azure OpenAI
"""

import streamlit as st
from PIL import Image
import io
import json
from diagram_analyzer import DiagramAnalyzer
from terraform_generator import TerraformGenerator
from cost_estimator import AzureCostEstimator
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Azure Architecture Analyzer Pro",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0078D4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .resource-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #0078D4;
    }
    .stat-box {
        background-color: #0078D4;
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .cost-box {
        background-color: #107C10;
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-size: 1.2rem;
    }
    .terraform-code {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'uploaded_image' not in st.session_state:
        st.session_state.uploaded_image = None
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    if 'terraform_code' not in st.session_state:
        st.session_state.terraform_code = None
    if 'cost_estimate' not in st.session_state:
        st.session_state.cost_estimate = None

def display_header():
    """Display the main header"""
    st.markdown('<div class="main-header">☁️ Azure Architecture Analyzer Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Analyze diagrams • Generate Terraform • Estimate costs</div>', unsafe_allow_html=True)

def configure_sidebar():
    """Configure the sidebar"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Azure OpenAI credentials
        azure_endpoint = st.text_input(
            "Azure OpenAI Endpoint",
            placeholder="https://your-resource.openai.azure.com/",
            help="Your Azure OpenAI endpoint URL"
        )
        
        api_key = st.text_input(
            "Azure OpenAI API Key",
            type="password",
            help="Enter your Azure OpenAI API key"
        )
        
        deployment_name = st.text_input(
            "Deployment Name",
            placeholder="gpt-4o",
            help="Your Azure OpenAI deployment name (e.g., gpt-4o, gpt-4-vision)"
        )
        
        api_version = st.selectbox(
            "API Version",
            options=["2024-02-15-preview", "2023-12-01-preview", "2023-07-01-preview"],
            index=0,
            help="Azure OpenAI API version"
        )
        
        # Azure region for cost estimation
        azure_region = st.selectbox(
            "Azure Region",
            options=[
                "East US",
                "West US",
                "Central US",
                "North Europe",
                "West Europe",
                "Southeast Asia",
                "East Asia",
                "UK South",
                "Australia East"
            ],
            index=0,
            help="Select Azure region for cost estimation"
        )
        
        st.markdown("---")
        
        # Information section
        st.header("ℹ️ Features")
        st.info("""
        ✅ Identify Azure resources  
        ✅ Generate Terraform code  
        ✅ Estimate monthly costs  
        ✅ Export IaC templates  
        ✅ Architecture analysis
        """)
        
        st.markdown("---")
        st.caption("💡 **Tip**: Use GPT-4o or GPT-4 Vision for best results")
        
        return api_key, azure_endpoint, deployment_name, api_version, azure_region

def display_upload_section():
    """Display file upload section"""
    st.header("📤 Upload Architecture Diagram")
    
    uploaded_file = st.file_uploader(
        "Choose a PNG image of your Azure architecture diagram",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a clear image"
    )
    
    return uploaded_file

def display_image_preview(image):
    """Display uploaded image"""
    st.header("🖼️ Uploaded Diagram")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(image, use_container_width=True, caption="Architecture Diagram")
    
    width, height = image.size
    st.caption(f"📐 {width} x {height} pixels | Format: {image.format}")

def display_statistics(result, cost_estimate):
    """Display statistics with cost"""
    st.header("📊 Analysis Statistics")
    
    resources = result.get('resources', [])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <h2>{len(resources)}</h2>
            <p>Total Resources</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        categories = set(r.get('category', 'Other') for r in resources)
        st.markdown(f"""
        <div class="stat-box">
            <h2>{len(categories)}</h2>
            <p>Categories</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        confidence = result.get('confidence', 'N/A')
        st.markdown(f"""
        <div class="stat-box">
            <h2>{confidence.upper()}</h2>
            <p>Confidence</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if cost_estimate:
            total_cost = cost_estimate.get('total_monthly_cost', 0)
            st.markdown(f"""
            <div class="cost-box">
                <h2>${total_cost:,.2f}</h2>
                <p>Est. Monthly Cost</p>
            </div>
            """, unsafe_allow_html=True)

def display_cost_breakdown(cost_estimate):
    """Display detailed cost breakdown"""
    st.header("💰 Cost Breakdown")
    
    if not cost_estimate or 'resources' not in cost_estimate:
        st.warning("No cost estimate available")
        return
    
    # Create DataFrame for cost table
    cost_data = []
    for resource in cost_estimate['resources']:
        cost_data.append({
            'Resource Name': resource['resource_name'],
            'Resource Type': resource['resource_type'],
            'Monthly Cost': f"${resource['estimated_monthly_cost']:.2f}",
            'Pricing Tier': resource.get('pricing_tier', 'Standard')
        })
    
    df = pd.DataFrame(cost_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Cost summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💵 Total Cost Summary")
        st.metric("Monthly Cost", f"${cost_estimate['total_monthly_cost']:,.2f}")
        st.metric("Annual Cost (Estimated)", f"${cost_estimate['total_monthly_cost'] * 12:,.2f}")
    
    with col2:
        st.subheader("📈 Top 3 Most Expensive")
        sorted_resources = sorted(
            cost_estimate['resources'],
            key=lambda x: x['estimated_monthly_cost'],
            reverse=True
        )[:3]
        
        for idx, resource in enumerate(sorted_resources, 1):
            st.write(f"{idx}. **{resource['resource_name']}**: ${resource['estimated_monthly_cost']:.2f}/month")

def display_terraform_code(terraform_code):
    """Display generated Terraform code"""
    st.header("🔧 Generated Terraform Code")
    
    if not terraform_code:
        st.warning("No Terraform code generated")
        return
    
    # Display tabs for different Terraform files
    tab1, tab2, tab3 = st.tabs(["main.tf", "variables.tf", "outputs.tf"])
    
    with tab1:
        st.code(terraform_code.get('main_tf', ''), language='hcl')
        st.download_button(
            "📥 Download main.tf",
            terraform_code.get('main_tf', ''),
            file_name="main.tf",
            mime="text/plain"
        )
    
    with tab2:
        st.code(terraform_code.get('variables_tf', ''), language='hcl')
        st.download_button(
            "📥 Download variables.tf",
            terraform_code.get('variables_tf', ''),
            file_name="variables.tf",
            mime="text/plain"
        )
    
    with tab3:
        st.code(terraform_code.get('outputs_tf', ''), language='hcl')
        st.download_button(
            "📥 Download outputs.tf",
            terraform_code.get('outputs_tf', ''),
            file_name="outputs.tf",
            mime="text/plain"
        )

def display_resources_by_category(result, analyzer):
    """Display resources grouped by category"""
    st.header("📦 Azure Resources by Category")
    
    categories = analyzer.get_resources_by_category(result)
    
    if not categories:
        st.warning("No resources identified")
        return
    
    category_tabs = st.tabs(list(categories.keys()))
    
    for tab, (category, resources) in zip(category_tabs, categories.items()):
        with tab:
            st.subheader(f"{category} ({len(resources)} resources)")
            
            for idx, resource in enumerate(resources, 1):
                with st.container():
                    st.markdown(f"""
                    <div class="resource-card">
                        <h4>#{idx} {resource.get('resource_name', 'Unnamed')}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Type:** {resource.get('resource_type', 'N/A')}")
                        st.write(f"**Description:** {resource.get('description', 'No description')}")
                    
                    with col2:
                        connections = resource.get('connections', [])
                        if connections:
                            st.write("**Connected to:**")
                            for conn in connections:
                                st.write(f"→ {conn}")
                    
                    st.markdown("---")

def main():
    """Main application logic"""
    initialize_session_state()
    display_header()
    
    # Configure sidebar
    api_key, azure_endpoint, deployment_name, api_version, azure_region = configure_sidebar()
    
    # Upload section
    uploaded_file = display_upload_section()
    
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.session_state.uploaded_image = image
            
            display_image_preview(image)
            
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                analyze_button = st.button(
                    "🔍 Analyze & Generate",
                    type="primary",
                    use_container_width=True
                )
            
            if analyze_button:
                if not api_key or not azure_endpoint or not deployment_name:
                    st.error("⚠️ Please enter all Azure OpenAI credentials!")
                else:
                    try:
                        # Step 1: Analyze diagram
                        with st.spinner("🔄 Step 1/3: Analyzing diagram..."):
                            if st.session_state.analyzer is None:
                                st.session_state.analyzer = DiagramAnalyzer(
                                    api_key, azure_endpoint, deployment_name, api_version
                                )
                            
                            result = st.session_state.analyzer.analyze_diagram(image)
                            st.session_state.analysis_result = result
                        
                        if result.get('metadata', {}).get('success'):
                            st.success("✅ Diagram analysis completed!")
                            
                            # Step 2: Generate Terraform
                            with st.spinner("🔄 Step 2/3: Generating Terraform code..."):
                                tf_generator = TerraformGenerator(
                                    api_key, azure_endpoint, deployment_name, api_version
                                )
                                terraform_code = tf_generator.generate_terraform(result, azure_region)
                                st.session_state.terraform_code = terraform_code
                            
                            st.success("✅ Terraform code generated!")
                            
                            # Step 3: Estimate costs
                            with st.spinner("🔄 Step 3/3: Estimating costs..."):
                                cost_estimator = AzureCostEstimator(
                                    api_key, azure_endpoint, deployment_name, api_version
                                )
                                cost_estimate = cost_estimator.estimate_costs(result, azure_region)
                                st.session_state.cost_estimate = cost_estimate
                            
                            st.success("✅ Cost estimation completed!")
                        else:
                            st.error(f"⚠️ Analysis failed: {result.get('summary', 'Unknown error')}")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.exception(e)
            
            # Display results
            if st.session_state.analysis_result is not None:
                result = st.session_state.analysis_result
                
                if result.get('metadata', {}).get('success'):
                    st.markdown("---")
                    
                    # Statistics with cost
                    display_statistics(result, st.session_state.cost_estimate)
                    
                    st.markdown("---")
                    
                    # Cost breakdown
                    if st.session_state.cost_estimate:
                        display_cost_breakdown(st.session_state.cost_estimate)
                    
                    st.markdown("---")
                    
                    # Terraform code
                    if st.session_state.terraform_code:
                        display_terraform_code(st.session_state.terraform_code)
                    
                    st.markdown("---")
                    
                    # Resources by category
                    display_resources_by_category(result, st.session_state.analyzer)
        
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
    
    else:
        st.info("""
        👆 **Get Started:**
        1. Set up Azure OpenAI in your Azure portal
        2. Deploy a GPT-4 Vision or GPT-4o model
        3. Enter your credentials in the sidebar
        4. Upload your Azure architecture diagram
        5. Click 'Analyze & Generate' to:
           - Identify all Azure resources
           - Generate Terraform deployment code
           - Estimate monthly costs
        
        **What you'll get:**
        - Complete resource inventory
        - Ready-to-deploy Terraform code
        - Detailed cost breakdown
        - Architecture analysis
        """)

if __name__ == "__main__":
    main()