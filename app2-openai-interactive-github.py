import streamlit as st
from PIL import Image
import io
import json
from diagram_analyzer import DiagramAnalyzer
from terraform_generator import TerraformGenerator
from github_agent import GitHubAgent
from cost_estimator import AzureCostEstimator

# ---------------------------------------------------------
# Page Config
# ---------------------------------------------------------
st.set_page_config(
    page_title="EHS Azure Architecture Analyzer",
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
    if "cost_estimate" not in st.session_state:
        st.session_state.cost_estimate = None
    if "github_push_result" not in st.session_state:
        st.session_state.github_push_result = None

init_state()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("## ☁️ EHS Azure Architecture to Deployment")

# ---------------------------------------------------------
# Sidebar – Configuration
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔧 Azure OpenAI Configuration")

    api_key = st.text_input("API Key", type="password")
    azure_endpoint = st.text_input("Azure OpenAI Endpoint")
    deployment_name = st.text_input("Deployment Name", value="gpt-4o")
    api_version = st.selectbox(
        "API Version",
        ["2024-02-15-preview", "2023-12-01-preview"]
    )
    
    st.markdown("---")
    st.header("🐙 GitHub Configuration")
    
    github_token = st.text_input("GitHub Token", type="password", 
                                help="Personal Access Token with repo permissions")
    github_owner = st.text_input("Repository Owner", 
                                help="GitHub username or organization")
    github_repo = st.text_input("Repository Name")
    github_branch = st.text_input("Branch", value="main")
    github_directory = st.text_input("Terraform Directory", value="terraform",
                                    help="Directory path in repo to store .tf files")

# ---------------------------------------------------------
# Upload Diagram
# ---------------------------------------------------------
st.header("📤 Upload EHS approved Architecture Diagram")
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
                        ["Central India", "East US", "West Europe", "Southeast Asia", "UK South"],
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
    # Generate Terraform & Estimate Costs
    # -----------------------------------------------------
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_terraform_btn = st.button("🚀 Generate Terraform", type="primary", use_container_width=True)
    
    with col2:
        estimate_costs_btn = st.button("💰 Estimate Costs Only", use_container_width=True)
    
    if generate_terraform_btn or estimate_costs_btn:
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
            
            # Get the region from the first resource (or use default)
            selected_region = approved_resources[0].get("region", "Central India") if approved_resources else "Central India"

            # Generate Terraform if requested
            if generate_terraform_btn:
                tf_generator = TerraformGenerator(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    deployment_name=deployment_name,
                    api_version=api_version
                )

                with st.spinner("Generating Terraform code..."):
                    st.session_state.terraform_code = tf_generator.generate_terraform(
                        filtered_result,
                        region=selected_region
                    )
            
            # Estimate costs using AI-powered estimator
            cost_estimator = AzureCostEstimator(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                deployment_name=deployment_name,
                api_version=api_version
            )
            
            with st.spinner("Estimating costs with AI..."):
                st.session_state.cost_estimate = cost_estimator.estimate_costs(
                    filtered_result,
                    region=selected_region
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
        st.download_button(
            label="📥 Download main.tf",
            data=st.session_state.terraform_code.get("main_tf", ""),
            file_name="main.tf",
            mime="text/plain"
        )

    with tab2:
        st.code(st.session_state.terraform_code.get("variables_tf", ""), language="hcl")
        st.download_button(
            label="📥 Download variables.tf",
            data=st.session_state.terraform_code.get("variables_tf", ""),
            file_name="variables.tf",
            mime="text/plain"
        )

    with tab3:
        st.code(st.session_state.terraform_code.get("outputs_tf", ""), language="hcl")
        st.download_button(
            label="📥 Download outputs.tf",
            data=st.session_state.terraform_code.get("outputs_tf", ""),
            file_name="outputs.tf",
            mime="text/plain"
        )

# ---------------------------------------------------------
# Cost Estimation Display
# ---------------------------------------------------------
if st.session_state.cost_estimate:
    st.markdown("---")
    st.header("💰 AI-Powered Cost Estimation")
    
    cost_data = st.session_state.cost_estimate
    
    # Check for errors
    if 'error' in cost_data:
        st.error(f"Cost estimation error: {cost_data['error']}")
        st.info("Showing baseline estimates as fallback")
    
    # Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Monthly Cost", 
            f"${cost_data['total_monthly_cost']:.2f}",
            help="Estimated monthly infrastructure cost"
        )
    
    with col2:
        annual_cost = cost_data['total_monthly_cost'] * 12
        st.metric(
            "Annual Cost", 
            f"${annual_cost:.2f}",
            help="Estimated annual infrastructure cost"
        )
    
    with col3:
        st.metric(
            "Resources", 
            len(cost_data['resources']),
            help="Number of resources"
        )
    
    with col4:
        st.metric(
            "Region",
            cost_data.get('region', 'N/A'),
            help="Azure region for pricing"
        )
    
    # Resource-level costs with detailed breakdown
    st.subheader("📊 Resource Cost Breakdown")
    
    # Create expandable sections for each resource
    for resource in cost_data['resources']:
        cost = resource.get('estimated_monthly_cost', 0)
        name = resource.get('resource_name', 'Unknown')
        resource_type = resource.get('resource_type', 'Unknown')
        tier = resource.get('pricing_tier', 'Standard')
        assumptions = resource.get('assumptions', 'No details available')
        
        with st.expander(f"💵 {name} - ${cost:.2f}/month"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Type:** {resource_type}")
                st.write(f"**Pricing Tier:** {tier}")
                st.write(f"**Monthly Cost:** ${cost:.2f}")
                st.write(f"**Annual Cost:** ${cost * 12:.2f}")
            
            with col2:
                # Cost visualization
                percentage = (cost / cost_data['total_monthly_cost'] * 100) if cost_data['total_monthly_cost'] > 0 else 0
                st.metric("% of Total", f"{percentage:.1f}%")
            
            st.info(f"**Assumptions:** {assumptions}")
    
    # Cost comparison table
    st.subheader("📋 Summary Table")
    
    cost_table_data = []
    for resource in sorted(cost_data['resources'], key=lambda x: x.get('estimated_monthly_cost', 0), reverse=True):
        cost = resource.get('estimated_monthly_cost', 0)
        percentage = (cost / cost_data['total_monthly_cost'] * 100) if cost_data['total_monthly_cost'] > 0 else 0
        
        cost_table_data.append({
            "Resource": resource.get('resource_name', 'Unknown'),
            "Type": resource.get('resource_type', 'Unknown').replace('azurerm_', '').replace('_', ' ').title(),
            "Tier": resource.get('pricing_tier', 'Standard'),
            "Monthly": f"${cost:.2f}",
            "Annual": f"${cost * 12:.2f}",
            "% of Total": f"{percentage:.1f}%"
        })
    
    st.table(cost_table_data)
    
    # Disclaimer and additional info
    st.info(f"ℹ️ {cost_data.get('disclaimer', 'Cost estimates are approximate.')}")
    
    if 'estimate_date' in cost_data:
        st.caption(f"Estimate generated: {cost_data['estimate_date']}")
    
    # Cost optimization suggestions
    st.subheader("💡 Cost Optimization Tips")
    
    high_cost_resources = [r for r in cost_data['resources'] if r.get('estimated_monthly_cost', 0) > 100]
    
    if high_cost_resources:
        st.warning(f"⚠️ Found {len(high_cost_resources)} resource(s) with monthly cost > $100")
        
        with st.expander("View Optimization Suggestions"):
            st.markdown("""
            **General Cost Optimization Strategies:**
            
            1. **Right-size resources**: Review SKU/tier selections
            2. **Use Reserved Instances**: Save up to 72% with 1-3 year commitments
            3. **Enable Auto-shutdown**: For non-production VMs
            4. **Implement auto-scaling**: Scale down during off-peak hours
            5. **Use Azure Hybrid Benefit**: If you have existing licenses
            6. **Monitor and optimize storage**: Delete unused data, use appropriate tiers
            7. **Review networking costs**: Optimize data transfer patterns
            """)
    else:
        st.success("✅ All resources are within reasonable cost ranges")
    
    # Export cost estimate
    st.subheader("📤 Export Cost Estimate")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        cost_json = json.dumps(cost_data, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=cost_json,
            file_name="cost_estimate.json",
            mime="application/json"
        )
    
    with col2:
        # Markdown export
        cost_md = f"""# Azure Cost Estimate

## Summary
- **Total Monthly Cost:** ${cost_data['total_monthly_cost']:.2f}
- **Total Annual Cost:** ${cost_data['total_monthly_cost'] * 12:.2f}
- **Region:** {cost_data.get('region', 'N/A')}
- **Currency:** {cost_data.get('currency', 'USD')}

## Resources

"""
        for r in cost_data['resources']:
            cost_md += f"### {r.get('resource_name', 'Unknown')}\n"
            cost_md += f"- Type: {r.get('resource_type', 'Unknown')}\n"
            cost_md += f"- Monthly: ${r.get('estimated_monthly_cost', 0):.2f}\n"
            cost_md += f"- Tier: {r.get('pricing_tier', 'Standard')}\n"
            cost_md += f"- Assumptions: {r.get('assumptions', 'N/A')}\n\n"
        
        cost_md += f"\n---\n{cost_data.get('disclaimer', '')}\n"
        
        st.download_button(
            label="📥 Download as Markdown",
            data=cost_md,
            file_name="COST_ESTIMATE.md",
            mime="text/markdown"
        )

# ---------------------------------------------------------
# Push to GitHub (only after Terraform generation)
# ---------------------------------------------------------
if st.session_state.terraform_code and st.session_state.cost_estimate:
    st.markdown("---")
    st.header("🐙 Push to GitHub")
    
    st.info("💡 After reviewing the Terraform code and cost estimate, push to GitHub to trigger your CI/CD pipeline.")
    
    # Verify GitHub configuration
    github_configured = all([github_token, github_owner, github_repo])
    
    if not github_configured:
        st.warning("⚠️ Please configure GitHub settings in the sidebar to enable push functionality.")
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**Repository:** `{github_owner}/{github_repo}`")
            st.write(f"**Branch:** `{github_branch}`")
            st.write(f"**Directory:** `{github_directory}/`")
            st.write(f"**Files to push:** main.tf, variables.tf, outputs.tf, COST_ESTIMATE.md")
        
        with col2:
            if st.button("📤 Push to GitHub", type="primary"):
                with st.spinner("Pushing to GitHub..."):
                    github_agent = GitHubAgent(
                        api_key=api_key,
                        azure_endpoint=azure_endpoint,
                        deployment_name=deployment_name,
                        api_version=api_version
                    )
                    
                    result = github_agent.push_to_github(
                        github_token=github_token,
                        repo_owner=github_owner,
                        repo_name=github_repo,
                        terraform_code=st.session_state.terraform_code,
                        branch=github_branch,
                        directory=github_directory,
                        cost_estimate=st.session_state.cost_estimate
                    )
                    
                    st.session_state.github_push_result = result
        
        # Display push result
        if st.session_state.github_push_result:
            result = st.session_state.github_push_result
            
            if result.get("success"):
                st.success("✅ Successfully pushed to GitHub!")
                
                st.markdown(f"""
**Push Details:**
- **Commit Message:** {result['commit_message']}
- **Commit SHA:** `{result['commit_sha'][:7]}`
- **Branch:** `{result['branch']}`
- **Files Pushed:** {len(result['files_pushed'])}

**Links:**
- 🔗 [View Repository]({result['repository_url']})
- 📝 [View Commit]({result['commit_url']})
                """)
                
                st.info("🔄 Your GitHub Actions workflow should now be triggered automatically!")
                
                # Show next steps
                with st.expander("📋 Next Steps"):
                    st.markdown("""
                    1. **Monitor GitHub Actions**: Go to your repository's Actions tab
                    2. **Review the Plan**: Check the Terraform plan output
                    3. **Approve Deployment**: If using protected environments, approve the deployment
                    4. **Verify Resources**: Once deployed, verify resources in Azure Portal
                    5. **Monitor Costs**: Set up Azure Cost Management alerts
                    """)
                
            else:
                st.error(f"❌ Failed to push to GitHub: {result.get('error', 'Unknown error')}")
                
                st.markdown("""
**Troubleshooting:**
1. Verify your GitHub token has `repo` permissions
2. Ensure the repository exists and you have write access
3. Check that the branch exists (create it if needed)
4. Verify the Azure OpenAI credentials are correct
                """)

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown("---")
st.caption("Azure Architecture Analyzer | Powered by Azure OpenAI, AI Cost Estimator & GitHub Integration")