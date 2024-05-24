import streamlit as st
from bs4 import BeautifulSoup
import requests
import re
from st_copy_to_clipboard import st_copy_to_clipboard
from PIL import Image
import pytesseract
import io
from PyPDF2 import PdfReader
from PIL import Image
import shutil 
import streamlit as st



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

# Function to extract text from an uploaded image
def extract_text_from_image(image):
    img = Image.open(image)
    text = pytesseract.image_to_string(img)
    return text

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_file, pages=None):
    reader = PdfReader(pdf_file)
    text = ""
    if pages:
        for page_num in pages:
            text += reader.pages[page_num].extract_text()
    else:
        for page in reader.pages:
            text += page.extract_text()
    return text

# Streamlit app
st.title("Copy Pasta 🍝")
st.subheader("No more painful text (mobile) highlighting. Copy text from long articles with a few clicks")

st.write("""
1) Enter a URL, upload an image, or upload a PDF
2) Extract the text 
3) Add prefix (prompt) if you want to use it for prompting (use mine if you want to for summary)
""")

# Option to switch between URL, Image upload, and PDF upload
mode = st.radio("Choose input method:", ("URL", "Image Upload", "PDF Upload"))

if mode == "URL":
    # Input box for URL
    url = st.text_input("Enter the URL:")

    # Button to extract text
    if st.button("Extract Text"):
        if url:
            main_text = extract_text_from_url(url)
            st.session_state['main_text'] = main_text
            st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
        else:
            st.session_state['main_text'] = "Please enter a valid URL."
            st.session_state['main_text_with_prefix'] = "Please enter a valid URL."
elif mode == "Image Upload":
    # File uploader for image
    uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

    # Button to extract text from image
    if st.button("Extract Text from Image"):
        if uploaded_image:
            main_text = extract_text_from_image(uploaded_image)
            st.session_state['main_text'] = main_text
            st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
        else:
            st.session_state['main_text'] = "Please upload a valid image."
            st.session_state['main_text_with_prefix'] = "Please upload a valid image."
else:
    # File uploader for PDF
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

    if uploaded_pdf:
        # Option to select specific pages or extract all text
        all_pages = st.checkbox("Extract all pages")
        if not all_pages:
            page_range = st.text_input("Enter page range (e.g., 1-3 for pages 1 to 3):")
            if page_range:
                try:
                    start_page, end_page = map(int, page_range.split('-'))
                    pages = list(range(start_page - 1, end_page))  # Adjust for zero-based indexing
                except ValueError:
                    st.error("Invalid page range format. Please use the format 'start-end'.")
                    pages = None
            else:
                pages = None
        else:
            pages = None

        # Button to extract text from PDF
        if st.button("Extract Text from PDF"):
            main_text = extract_text_from_pdf(uploaded_pdf, pages)
            st.session_state['main_text'] = main_text
            st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text

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