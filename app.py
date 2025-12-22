import streamlit as st
from PIL import Image
import io

# Set page configuration
st.set_page_config(
    page_title="Architecture Diagram Viewer",
    page_icon="🏗️",
    layout="wide"
)

# Title and description
st.title("🏗️ Architecture Diagram Viewer")
st.write("Upload your architecture diagram in PNG format to view and analyze it.")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a PNG file",
    type=['png'],
    help="Upload an architecture diagram in PNG format"
)

# Display the uploaded image
if uploaded_file is not None:
    try:
        # Read and display the image
        image = Image.open(uploaded_file)
        
        # Create two columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Uploaded Diagram")
            st.image(image, use_container_width=True)
        
        with col2:
            st.subheader("Image Details")
            st.write(f"**Filename:** {uploaded_file.name}")
            st.write(f"**Size:** {uploaded_file.size / 1024:.2f} KB")
            st.write(f"**Dimensions:** {image.size[0]} x {image.size[1]} pixels")
            st.write(f"**Format:** {image.format}")
            st.write(f"**Mode:** {image.mode}")
            
            # Download button
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            byte_im = buf.getvalue()
            
            st.download_button(
                label="Download Image",
                data=byte_im,
                file_name=uploaded_file.name,
                mime="image/png"
            )
        
        st.success("✅ Architecture diagram uploaded successfully!")
        
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
else:
    # Instructions when no file is uploaded
    st.info("👆 Please upload a PNG architecture diagram to get started.")
    
    # Optional: Add example or instructions
    with st.expander("ℹ️ How to use this app"):
        st.write("""
        1. Click the 'Browse files' button above
        2. Select a PNG file containing your architecture diagram
        3. The diagram will be displayed along with its details
        4. You can download the image using the download button
        """)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit 🎈")