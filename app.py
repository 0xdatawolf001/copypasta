import streamlit as st
import requests
from bs4 import BeautifulSoup

# Function to extract text from a webpage
def extract_text_from_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text(separator=' ')
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text

# Streamlit app
def main():
    st.title("Copy Pasta 🍝")
    st.subheader("Paste Link, Get Text, One Click Copy. No more max main text highlighting")
    
    if 'extracted_text' not in st.session_state:
        st.session_state['extracted_text'] = ''
    
    if 'full_text' not in st.session_state:
        st.session_state['full_text'] = ''
    
    url = st.text_input("Enter the URL of the website:")

    if st.button("Extract Text"):
        if url:
            try:
                st.session_state['extracted_text'] = extract_text_from_website(url)
                st.session_state['full_text'] = st.session_state['extracted_text']
                st.success("Text extraction successful!")
            except Exception as e:
                st.error("An error occurred during text extraction.")
                st.error(str(e))
        else:
            st.warning("Please enter a URL.")
    
    # Toggle button for prefix paragraph
    add_prefix = st.checkbox("Add Prefix Paragraph")
    
    # Default prefix paragraph text
    default_prefix = ("Extract the key insights and takeaways. Write in point form and organize section in headers. "
                      "Make sure it is comprehensive and complete and you don’t lose out important information. "
                      "At the end, have a call to action on the next steps based on what the write up suggests.")
    
    if add_prefix:
        prefix_paragraph = st.text_area("Prefix Paragraph", value=default_prefix, height=150)
    else:
        prefix_paragraph = ""
    
    if st.button("Refresh Text To Copy"):
        st.session_state['full_text'] = f"{prefix_paragraph}\n\n{st.session_state['extracted_text']}" if add_prefix else st.session_state['extracted_text']
    
    st.text_area("Full Text:", value=st.session_state['full_text'], height=400)
    
    if st.button("Copy to Clipboard"):
        full_text = st.session_state.get('full_text', '')
        st.markdown(
            f"""
            <script>
            function copyToClipboard(text) {{
                if (navigator.clipboard) {{
                    navigator.clipboard.writeText(text).then(function() {{
                        console.log('Text copied to clipboard');
                    }}, function(err) {{
                        console.error('Could not copy text: ', err);
                    }});
                }} else {{
                    var textArea = document.createElement("textarea");
                    textArea.value = text;
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    try {{
                        document.execCommand('copy');
                        console.log('Text copied to clipboard');
                    }} catch (err) {{
                        console.error('Could not copy text: ', err);
                    }}
                    document.body.removeChild(textArea);
                }}
            }}
            copyToClipboard(`{full_text}`);
            </script>
            """,
            unsafe_allow_html=True
        )
        st.success("Text copied to clipboard!")

if __name__ == "__main__":
    main()