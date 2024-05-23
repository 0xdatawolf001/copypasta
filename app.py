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
    url = st.text_input("Enter the URL of the website:")

    if st.button("Extract Text"):
        if url:
            try:
                st.session_state['extracted_text'] = extract_text_from_website(url)
                st.text_area("Extracted Text:", value=st.session_state['extracted_text'], height=400)
                st.success("Text extraction successful!")
            except Exception as e:
                st.error("An error occurred during text extraction.")
                st.error(str(e))
        else:
            st.warning("Please enter a URL.")

    if st.button("Copy to Clipboard"):
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
            copyToClipboard(`{st.session_state['extracted_text']}`);
            </script>
            """,
            unsafe_allow_html=True
        )
        st.success("Text copied to clipboard!")

if __name__ == "__main__":
    main()