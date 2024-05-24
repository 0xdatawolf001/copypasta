# import streamlit as st
# from bs4 import BeautifulSoup
# import requests
# import re
# from st_copy_to_clipboard import st_copy_to_clipboard

# # Function to extract main body text from a URL
# def extract_text_from_url(url):
#     response = requests.get(url)
#     soup = BeautifulSoup(response.content, 'html.parser')
    
#     # Try to find the main content in common tags
#     main_content = soup.find('article') or soup.find('div', {'class': 'main-content'}) or soup.find('body')
    
#     if main_content:
#         # Extract text from paragraphs and divs
#         paragraphs = main_content.find_all(['p', 'div'])
#         text = "\n".join([para.get_text(separator=' ', strip=True) for para in paragraphs])
        
#         # Clean up excessive whitespace
#         text = re.sub(r'\s+', ' ', text).strip()
#         return text
#     else:
#         return "No main body text found."

# # Streamlit app
# st.title("Copy Pasta 🍝")
# st.subheader("No more painful text (mobile) highlighting. Copy text from long articles with a few clicks")

# st.write("""
# 1) Enter a URL
# 2) Extract the text 
# 3) Add prefix (prompt) if you want to use it for prompting (use mine if you want to for summary)
# """)

# # Input box for URL
# url = st.text_input("Enter the URL:")

# # Button to extract text
# if st.button("Extract Text"):
#     if url:
#         main_text = extract_text_from_url(url)
#         st.session_state['main_text'] = main_text
#         st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
#     else:
#         st.session_state['main_text'] = "Please enter a valid URL."
#         st.session_state['main_text_with_prefix'] = "Please enter a valid URL."

# # Display extracted text
# if 'main_text' in st.session_state:
#     st.text_area("Extracted Text:", st.session_state['main_text'], height=300)

# # Checkbox for adding prefix
# add_prefix = st.checkbox("Add Prefix Prompt Paragraph")

# # Default prefix text
# default_prefix = ("Extract the key insights and takeaways. Write in point form and organize section in headers. "
#                   "Make sure it is comprehensive and complete and you don’t lose out important information. "
#                   "At the end, have a call to action on the next steps based on what the write up suggests.")

# # Text area for prefix if checkbox is checked
# if add_prefix:
#     prefix_text = st.text_area("Prefix Text:", default_prefix, height=100)
    
#     # Button to refresh and add prefix to main text
#     if st.button("Refresh with Prefix"):
#         if 'main_text' in st.session_state:
#             st.session_state['main_text_with_prefix'] = prefix_text + "\n\n" + st.session_state['main_text']
# else:
#     # If the prefix is removed, revert to the original text
#     if 'main_text' in st.session_state:
#         st.session_state['main_text_with_prefix'] = st.session_state['main_text']
#         if 'main_text_with_prefix' in st.session_state:
#             del st.session_state['main_text_with_prefix']

# # Display text with prefix if available
# if 'main_text_with_prefix' in st.session_state:
#     st.text_area("Text with Prefix (Prompt):", st.session_state['main_text_with_prefix'], height=300)

# # Button to copy text to clipboard
# if 'main_text_with_prefix' in st.session_state:
#     st_copy_to_clipboard(st.session_state['main_text_with_prefix'])
# elif 'main_text' in st.session_state:
#     st_copy_to_clipboard(st.session_state['main_text'])

# st.write("This is a simple app that literally copies everything on the page so that it is easier to copy large amount of text for prompting on Mobile")



import streamlit as st
from bs4 import BeautifulSoup
import requests
import re
from st_copy_to_clipboard import st_copy_to_clipboard
from PyPDF2 import PdfReader

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

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf, start_page=None, end_page=None):
    pdf_reader = PdfReader(pdf)
    text = ""
    if start_page is not None and end_page is not None:
        for page_num in range(start_page, end_page + 1):
            text += pdf_reader.pages[page_num].extract_text()
    else:
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Streamlit app
st.title("Copy Pasta 🍝")
st.subheader("No more painful text (mobile) highlighting. Copy text from long articles with a few clicks")

st.write("""
1) Enter a URL or upload a PDF
2) Extract the text 
3) Add prefix (prompt) if you want to use it for prompting (use mine if you want to for summary)
""")

# Input box for URL
url = st.text_input("Enter the URL:")

# File uploader for PDF
uploaded_pdf = st.file_uploader("Upload a PDF file", type="pdf")

# Input for page range
page_range = st.text_input("Enter page range (e.g., 0-2) or leave empty to extract all pages:")

# Button to extract text
if st.button("Extract Text"):
    if url:
        main_text = extract_text_from_url(url)
        st.session_state['main_text'] = main_text
        st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
    elif uploaded_pdf:
        if page_range:
            start_page, end_page = map(int, page_range.split('-'))
            main_text = extract_text_from_pdf(uploaded_pdf, start_page, end_page)
        else:
            main_text = extract_text_from_pdf(uploaded_pdf)
        st.session_state['main_text'] = main_text
        st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
    else:
        st.session_state['main_text'] = "Please enter a valid URL or upload a PDF."
        st.session_state['main_text_with_prefix'] = "Please enter a valid URL or upload a PDF."

# Display extracted text
if 'main_text' in st.session_state:
    st.text_area("Extracted Text:", st.session_state['main_text'], height=300)

# Checkbox for adding prefix
add_prefix = st.checkbox("Add Prefix Prompt Paragraph")

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
    # If the prefix is removed, revert to the original text
    if 'main_text' in st.session_state:
        st.session_state['main_text_with_prefix'] = st.session_state['main_text']
        if 'main_text_with_prefix' in st.session_state:
            del st.session_state['main_text_with_prefix']

# Display text with prefix if available
if 'main_text_with_prefix' in st.session_state:
    st.text_area("Text with Prefix (Prompt):", st.session_state['main_text_with_prefix'], height=300)

# Button to copy text to clipboard
if 'main_text_with_prefix' in st.session_state:
    st_copy_to_clipboard(st.session_state['main_text_with_prefix'])
elif 'main_text' in st.session_state:
    st_copy_to_clipboard(st.session_state['main_text'])

st.write("This is a simple app that literally copies everything on the page so that it is easier to copy large amount of text for prompting on Mobile")
