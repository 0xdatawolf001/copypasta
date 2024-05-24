import streamlit as st
from bs4 import BeautifulSoup
import requests
import pyperclip
import re

# Function to extract main body text from a URL
def extract_text_from_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Try to find the main content in common tags
    main_content = soup.find('article') or soup.find('div', {'class': 'main-content'}) or soup.find('body')
    
    if main_content:
        # Extract text from paragraphs and divs
        paragraphs = main_content.find_all(['p', 'div'])
        text = "\n".join([para.get_text(separator=' ', strip=True) for para in paragraphs])
        
        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    else:
        return "No main body text found."

# Streamlit app
st.title("Copy Pasta 🍝")
st.subheader("No more painful text highlighting. Copy text from long articles with a few clicks")

st.write("""
1) Enter a URL
2) Extract the text 
3) Add prefix if you want to use it for prompting (use mine if you want to for summary)
""")

# Input box for URL
url = st.text_input("Enter the URL:")

# Button to extract text
if st.button("Extract Text"):
    if url:
        main_text = extract_text_from_url(url)
        st.session_state['main_text'] = main_text
    else:
        st.session_state['main_text'] = "Please enter a valid URL."

# Display extracted text
if 'main_text' in st.session_state:
    st.text_area("Extracted Text:", st.session_state['main_text'], height=300)

# Checkbox for adding prefix
add_prefix = st.checkbox("Add Prefix Paragraph")

# Default prefix text
default_prefix = ("Extract the key insights and takeaways. Write in point form and organize section in headers. "
                  "Make sure it is comprehensive and complete and you don’t lose out important information. "
                  "At the end, have a call to action on the next steps based on what the write up suggests.")

# Text area for prefix if checkbox is checked
if add_prefix:
    prefix_text = st.text_area("Prefix Text:", default_prefix, height=100)
    
    # Button to refresh and add prefix to main text
    if st.button("Refresh with Prefix"):
        if 'main_text' in st.session_state:
            st.session_state['main_text_with_prefix'] = prefix_text + "\n\n" + st.session_state['main_text']
        else:
            st.session_state['main_text_with_prefix'] = prefix_text

# Display text with prefix if available
if 'main_text_with_prefix' in st.session_state:
    st.text_area("Text with Prefix:", st.session_state['main_text_with_prefix'], height=300)

# Button to copy text to clipboard
if st.button("Copy to Clipboard"):
    if 'main_text_with_prefix' in st.session_state:
        pyperclip.copy(st.session_state['main_text_with_prefix'])
    elif 'main_text' in st.session_state:
        pyperclip.copy(st.session_state['main_text'])
    st.success("Text copied to clipboard!")

st.write("This is a simple app that literally copies everything on the page so that it is easier to copy large amount of text to be added into prompting on Mobile")
