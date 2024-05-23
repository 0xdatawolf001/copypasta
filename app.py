import streamlit as st
import requests
from bs4 import BeautifulSoup
import pyperclip  # Install with: pip install pyperclip

# Function to extract text from a webpage
def extract_text_from_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text(separator=' ')
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text

# Streamlit app
def main():
    st.title("Webpage Text Extractor and Copier")
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
        try:
            pyperclip.copy(st.session_state['extracted_text'])
            st.success("Text copied to clipboard!")
        except:
            st.error("Sorry, unable to copy the text. Please try again.")

if __name__ == "__main__":
    main()