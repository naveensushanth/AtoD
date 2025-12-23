"""
Azure Architecture Diagram Analyzer - Streamlit User Interface
This module provides a web-based UI for uploading and analyzing Azure architecture diagrams.
Users can upload PNG images and receive detailed analysis of Azure resources.
"""

import streamlit as st
from PIL import Image
import io
import json
from diagram_analyzer import DiagramAnalyzer
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Azure Architecture Diagram Analyzer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
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

def display_header():
    """Display the main header"""
    st.markdown('<div class="main-header">☁️ Azure Architecture Diagram Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload your architecture diagram and discover all Azure resources instantly</div>', unsafe_allow_html=True)

def configure_sidebar():
    """Configure the sidebar with API key input and settings"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key. Get one at https://aistudio.google.com/app/apikey"
        )
        
        # Model selection with corrected names
        model_name = st.selectbox(
            "AI Model",
            options=[
                "gemini-1.5-flash-latest",
                "gemini-1.5-pro-latest"
            ],
            index=0,
            help="Select the Gemini model to use for analysis. Flash is faster, Pro is more accurate."
        )
        
        st.markdown("---")
        
        # Test API Key button
        if api_key:
            if st.button("🧪 Test API Key", use_container_width=True):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    models = genai.list_models()
                    st.success("✅ API Key is valid!")
                    
                    with st.expander("📋 Available Models"):
                        for model in models:
                            if 'generateContent' in model.supported_generation_methods:
                                st.text(f"• {model.name}")
                except Exception as e:
                    st.error(f"❌ API Key Error: {str(e)}")
        
        st.markdown("---")
        
        # Information section
        st.header("ℹ️ About")
        st.info("""
        This tool analyzes Azure architecture diagrams using AI to:
        
        ✅ Identify all Azure resources  
        ✅ Detect architecture patterns  
        ✅ Map resource connections  
        ✅ Categorize services  
        ✅ Export results (JSON/CSV)
        """)
        
        st.markdown("---")
        
        # Instructions
        with st.expander("📖 How to Use"):
            st.markdown("""
            **Step 1: Get API Key**
            1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
            2. Sign in with Google account
            3. Click "Create API Key"
            4. Copy and paste it above
            
            **Step 2: Analyze Diagram**
            1. Upload a PNG architecture diagram
            2. Click 'Analyze Diagram'
            3. Review the identified resources
            4. Export results if needed
            
            **Supported Format:** PNG images
            
            **Best Results:** Clear diagrams with visible service icons and labels
            """)
        
        # Troubleshooting section
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Issues:**
            
            • **"404 model not found"** - API key might be invalid or model unavailable
            • **"Invalid API key"** - Check your API key at Google AI Studio
            • **Slow analysis** - Large images take longer; try using Flash model
            • **Low confidence results** - Ensure diagram has clear labels and icons
            
            **Tips for Better Results:**
            • Use high-resolution images
            • Ensure text/labels are readable
            • Include Azure service icons
            • Avoid heavily compressed images
            """)
        
        return api_key, model_name

def display_upload_section():
    """Display the file upload section"""
    st.header("📤 Upload Architecture Diagram")
    
    uploaded_file = st.file_uploader(
        "Choose a PNG image of your Azure architecture diagram",
        type=['png'],
        help="Upload a clear PNG image of your architecture diagram"
    )
    
    return uploaded_file

def display_image_preview(image):
    """Display the uploaded image preview"""
    st.header("🖼️ Uploaded Diagram")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(image, use_container_width=True, caption="Architecture Diagram Preview")
    
    # Display image info
    width, height = image.size
    st.caption(f"📏 Image dimensions: {width} x {height} pixels | Format: {image.format}")

def display_statistics(result):
    """Display summary statistics in a nice layout"""
    st.header("📊 Analysis Statistics")
    
    resources = result.get('resources', [])
    metadata = result.get('metadata', {})
    
    # Create columns for statistics
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
        total_connections = sum(len(r.get('connections', [])) for r in resources)
        st.markdown(f"""
        <div class="stat-box">
            <h2>{total_connections}</h2>
            <p>Connections</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        confidence = result.get('confidence', 'N/A')
        st.markdown(f"""
        <div class="stat-box">
            <h2>{confidence.upper()}</h2>
            <p>Confidence</p>
        </div>
        """, unsafe_allow_html=True)

def display_architecture_overview(result):
    """Display the architecture pattern and summary"""
    st.header("🗺️ Architecture Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Architecture Pattern")
        st.info(result.get('architecture_pattern', 'Not identified'))
    
    with col2:
        st.subheader("Confidence Level")
        confidence = result.get('confidence', 'N/A')
        if confidence.lower() == 'high':
            st.success(f"✅ {confidence.upper()}")
        elif confidence.lower() == 'medium':
            st.warning(f"⚠️ {confidence.upper()}")
        else:
            st.error(f"❌ {confidence.upper()}")
    
    st.subheader("Summary")
    st.write(result.get('summary', 'No summary available'))

def display_resources_by_category(result, analyzer):
    """Display resources grouped by category"""
    st.header("📦 Azure Resources by Category")
    
    categories = analyzer.get_resources_by_category(result)
    
    if not categories:
        st.warning("No resources identified in the diagram.")
        return
    
    # Create tabs for each category
    category_tabs = st.tabs(list(categories.keys()))
    
    for tab, (category, resources) in zip(category_tabs, categories.items()):
        with tab:
            st.subheader(f"{category} ({len(resources)} resources)")
            
            for idx, resource in enumerate(resources, 1):
                with st.container():
                    st.markdown(f"""
                    <div class="resource-card">
                        <h4>#{idx} {resource.get('resource_name', 'Unnamed Resource')}</h4>
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
                        else:
                            st.write("**No connections**")
                    
                    st.markdown("---")

def display_resources_table(result):
    """Display all resources in a table format"""
    st.header("📋 All Resources (Table View)")
    
    resources = result.get('resources', [])
    
    if not resources:
        st.warning("No resources to display.")
        return
    
    # Create DataFrame
    df_data = []
    for resource in resources:
        df_data.append({
            'Resource Name': resource.get('resource_name', ''),
            'Type': resource.get('resource_type', ''),
            'Category': resource.get('category', ''),
            'Connections': len(resource.get('connections', [])),
            'Description': resource.get('description', '')[:100] + '...' if len(resource.get('description', '')) > 100 else resource.get('description', '')
        })
    
    df = pd.DataFrame(df_data)
    
    # Display with filtering
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

def display_export_options(result, analyzer):
    """Display export options for the analysis results"""
    st.header("💾 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export as JSON
        json_str = json.dumps(result, indent=2)
        st.download_button(
            label="📄 Download JSON",
            data=json_str,
            file_name=f"azure_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # Export as CSV
        resources = result.get('resources', [])
        if resources:
            df_data = []
            for resource in resources:
                df_data.append({
                    'Resource Name': resource.get('resource_name', ''),
                    'Resource Type': resource.get('resource_type', ''),
                    'Category': resource.get('category', ''),
                    'Description': resource.get('description', ''),
                    'Connections': '; '.join(resource.get('connections', [])),
                    'Connection Count': len(resource.get('connections', []))
                })
            
            df = pd.DataFrame(df_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📊 Download CSV",
                data=csv,
                file_name=f"azure_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col3:
        # Export full report as text
        report = f"""Azure Architecture Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ARCHITECTURE PATTERN
{result.get('architecture_pattern', 'N/A')}

SUMMARY
{result.get('summary', 'N/A')}

CONFIDENCE LEVEL
{result.get('confidence', 'N/A')}

RESOURCES IDENTIFIED
Total: {len(result.get('resources', []))}

"""
        for idx, resource in enumerate(result.get('resources', []), 1):
            report += f"\n{idx}. {resource.get('resource_name', 'Unnamed')}\n"
            report += f"   Type: {resource.get('resource_type', 'N/A')}\n"
            report += f"   Category: {resource.get('category', 'N/A')}\n"
            report += f"   Description: {resource.get('description', 'N/A')}\n"
            if resource.get('connections'):
                report += f"   Connections: {', '.join(resource.get('connections'))}\n"
        
        st.download_button(
            label="📝 Download Report",
            data=report,
            file_name=f"azure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

def main():
    """Main application logic"""
    initialize_session_state()
    display_header()
    
    # Configure sidebar and get settings
    api_key, model_name = configure_sidebar()
    
    # Main content area
    uploaded_file = display_upload_section()
    
    # Process uploaded file
    if uploaded_file is not None:
        try:
            # Convert uploaded file to PIL Image
            image = Image.open(uploaded_file)
            st.session_state.uploaded_image = image
            
            # Display image preview
            display_image_preview(image)
            
            # Analyze button
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                analyze_button = st.button(
                    "🔍 Analyze Diagram",
                    type="primary",
                    use_container_width=True
                )
            
            # Perform analysis
            if analyze_button:
                if not api_key:
                    st.error("⚠️ Please enter your Google Gemini API key in the sidebar!")
                else:
                    try:
                        with st.spinner("🔄 Analyzing your architecture diagram... This may take 10-30 seconds..."):
                            # Initialize analyzer if not already done
                            if st.session_state.analyzer is None or st.session_state.analyzer.api_key != api_key:
                                st.session_state.analyzer = DiagramAnalyzer(api_key, model_name)
                            
                            # Perform analysis
                            result = st.session_state.analyzer.analyze_diagram(image)
                            st.session_state.analysis_result = result
                        
                        if result.get('metadata', {}).get('success'):
                            st.success("✅ Analysis completed successfully!")
                        else:
                            st.error(f"⚠️ Analysis encountered issues: {result.get('summary', 'Unknown error')}")
                    
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
                        st.exception(e)
            
            # Display results if available
            if st.session_state.analysis_result is not None:
                result = st.session_state.analysis_result
                
                if result.get('metadata', {}).get('success'):
                    st.markdown("---")
                    
                    # Display statistics
                    display_statistics(result)
                    
                    st.markdown("---")
                    
                    # Display architecture overview
                    display_architecture_overview(result)
                    
                    st.markdown("---")
                    
                    # Display resources by category
                    display_resources_by_category(result, st.session_state.analyzer)
                    
                    st.markdown("---")
                    
                    # Display resources table
                    display_resources_table(result)
                    
                    st.markdown("---")
                    
                    # Display export options
                    display_export_options(result, st.session_state.analyzer)
                else:
                    st.error("Analysis was not successful. Please check the error message above.")
        
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
            st.exception(e)
    
    else:
        # Show example/help when no file is uploaded
        st.info("""
        👆 **Get Started:**
        1. Get your FREE Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
        2. Enter the API key in the sidebar
        3. Upload a PNG image of your Azure architecture diagram
        4. Click 'Analyze Diagram' to extract all Azure resources
        
        **What you'll get:**
        - Complete list of all Azure resources
        - Resource connections and relationships
        - Architecture pattern identification
        - Exportable results (JSON, CSV, Text)
        """)
        
        # Example placeholder
        st.markdown("---")
        st.subheader("💡 Example Output")
        st.write("After analyzing your diagram, you'll see:")
        st.write("• Resource breakdown by category (Compute, Storage, Database, etc.)")
        st.write("• Detailed information about each component")
        st.write("• Connection mappings between resources")
        st.write("• Architecture pattern recognition")

if __name__ == "__main__":
    main()