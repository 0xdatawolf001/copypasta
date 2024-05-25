# import streamlit as st
# from bs4 import BeautifulSoup
# import requests
# import re
# from st_copy_to_clipboard import st_copy_to_clipboard
# import PyPDF2
# import io
# import base64
# from easyocr import Reader

# # Function to extract main body text from a URL
# def extract_text_from_url(url):
#     response = requests.get(url)
#     content_type = response.headers.get('Content-Type')
    
#     if 'application/pdf' in content_type:
#         # If the URL points to a PDF, extract text from the PDF
#         pdf_file = io.BytesIO(response.content)
#         pdf_reader = PyPDF2.PdfReader(pdf_file)
#         return extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
#     else:
#         # Otherwise, extract text from the HTML content
#         soup = BeautifulSoup(response.content, 'html.parser')
#         main_content = soup.find('article') or soup.find('div', {'class': 'main-content'}) or soup.find('body')
        
#         if main_content:
#             paragraphs = main_content.find_all(['p', 'div'])
#             text = "\n".join([para.get_text(separator=' ', strip=True) for para in paragraphs])
#             text = re.sub(r'\s+', ' ', text).strip()
#             return text
#         else:
#             return "No main body text found."

# # Function to extract text from a PDF
# def extract_text_from_pdf(pdf_reader, start_page, end_page):
#     num_pages = len(pdf_reader.pages)
#     start_page = max(0, start_page - 1)  # Convert to zero-based index
#     end_page = min(num_pages - 1, end_page - 1)  # Convert to zero-based index
    
#     text = ""
#     for page_num in range(start_page, end_page + 1):
#         page = pdf_reader.pages[page_num]
#         text += page.extract_text() + "\n"
    
#     return text

# # Function to display PDF pages
# def display_pdf_pages(pdf_file, start_page, end_page):
#     pdf_reader = PyPDF2.PdfReader(pdf_file)
#     num_pages = len(pdf_reader.pages)
#     start_page = max(0, start_page - 1)  # Convert to zero-based index
#     end_page = min(num_pages - 1, end_page - 1)  # Convert to zero-based index
    
#     output = PyPDF2.PdfWriter()
#     for page_num in range(start_page, end_page + 1):
#         output.add_page(pdf_reader.pages[page_num])
    
#     pdf_bytes = io.BytesIO()
#     output.write(pdf_bytes)
#     pdf_bytes.seek(0)
    
#     base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
#     pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
#     st.markdown(pdf_display, unsafe_allow_html=True)

# # Function to extract text from an image using EasyOCR
# def extract_text_from_image(image_file):
#     reader = Reader(['en'], gpu=False) # change language if needed
#     try:
#         image = image_file.read()
#         result = reader.readtext(image)
#         extracted_text = '\n'.join([text[1] for text in result])
#         return extracted_text
#     except ValueError as e:
#         st.error(f"Error extracting text from image: {e}")
#         return None

# # Streamlit app
# st.title("Copy Pasta 🍝")
# st.subheader("No more painful text (mobile) highlighting. Copy text from long articles with a few clicks")
# st.write("This is a simple app that copies text from the upload files or URL so that it is easier to copy large amount of text for prompting. It is not a LLM")
# st.write("""
# 1) Enter a URL or upload a PDF or Image
# 2) Extract the text 
# 3) Add prefix (prompt) if you want to use it for prompting (use mine if you want to for summary)
# """)

# # Option to choose between URL, PDF, and Image
# option = st.radio("Choose input type:", ("URL", "PDF", "Image"))

# if option == "PDF (Does not work with scans)":
#     pdf_file = st.file_uploader("Upload a PDF file", type="pdf")
    
#     if pdf_file:
#         all_pages = st.checkbox("OCR all pages")
        
#         if not all_pages:
#             start_page = st.number_input("Starting Page Number", min_value=1, step=1)
#             end_page = st.number_input("Ending Page Number", min_value=1, step=1)
            
#             if st.button("Extract Text from PDF"):
#                 if start_page and end_page:
#                     if start_page > end_page:
#                         start_page, end_page = end_page, start_page
#                     pdf_reader = PyPDF2.PdfReader(pdf_file)
#                     main_text = extract_text_from_pdf(pdf_reader, start_page, end_page)
#                     st.session_state['main_text'] = main_text
#                     st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
#                     display_pdf_pages(pdf_file, start_page, end_page)  # Display the selected pages
#                 else:
#                     st.error("Please enter valid page numbers.")
#         else:
#             if st.button("Extract Text from PDF"):
#                 pdf_reader = PyPDF2.PdfReader(pdf_file)
#                 main_text = extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
#                 st.session_state['main_text'] = main_text
#                 st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
#                 display_pdf_pages(pdf_file, 1, len(pdf_reader.pages))  # Display all pages

# elif option == "URL":
#     # Input box for URL
#     url = st.text_input("Enter the URL:")
    
#     # Button to extract text
#     if st.button("Extract Text"):
#         if url:
#             main_text = extract_text_from_url(url)
#             st.session_state['main_text'] = main_text
#             st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
#         else:
#             st.session_state['main_text'] = "Please enter a valid URL."
#             st.session_state['main_text_with_prefix'] = "Please enter a valid URL."

# elif option == "Image":
#     image_file = st.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])
#     if image_file:
#         if st.button("Extract Text from Image"):
#             extracted_text = extract_text_from_image(image_file)
#             if extracted_text:
#                 st.session_state['main_text'] = extracted_text
#                 st.session_state['main_text_with_prefix'] = extracted_text

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
import PyPDF2
import io
import base64
from easyocr import Reader
from PIL import Image
import numpy as np
import fitz 

# Function to extract main body text from a URL
def extract_text_from_url(url):
    response = requests.get(url)
    content_type = response.headers.get('Content-Type')
    
    if 'application/pdf' in content_type:
        # If the URL points to a PDF, extract text from the PDF
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
    else:
        # Otherwise, extract text from the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        main_content = soup.find('article') or soup.find('div', {'class': 'main-content'}) or soup.find('body')
        
        if main_content:
            paragraphs = main_content.find_all(['p', 'div'])
            text = "\n".join([para.get_text(separator=' ', strip=True) for para in paragraphs])
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        else:
            return "No main body text found."

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_reader, start_page, end_page):
    num_pages = len(pdf_reader.pages)
    start_page = max(0, start_page - 1)  # Convert to zero-based index
    end_page = min(num_pages - 1, end_page - 1)  # Convert to zero-based index
    
    text = ""
    for page_num in range(start_page, end_page + 1):
        page = pdf_reader.pages[page_num]
        text += page.extract_text() + "\n"
    
    return text

# # Function to display PDF pages
# def display_pdf_pages(pdf_file, start_page, end_page):
#     pdf_reader = PyPDF2.PdfReader(pdf_file)
#     num_pages = len(pdf_reader.pages)
#     start_page = max(0, start_page - 1)  # Convert to zero-based index
#     end_page = min(num_pages - 1, end_page - 1)  # Convert to zero-based index
    
#     output = PyPDF2.PdfWriter()
#     for page_num in range(start_page, end_page + 1):
#         output.add_page(pdf_reader.pages[page_num])
    
#     pdf_bytes = io.BytesIO()
#     output.write(pdf_bytes)
#     pdf_bytes.seek(0)
    
#     base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
#     pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
#     st.markdown(pdf_display, unsafe_allow_html=True)

def extract_text_from_image(image):  # Receive image as argument
    reader = Reader(['en'], gpu=False)  # change language if needed
    try:
        # Convert image to NumPy array for EasyOCR
        image_np = np.array(image) 
        result = reader.readtext(image_np)
        extracted_text = '\n'.join([text[1] for text in result])
        return extracted_text
    except ValueError as e:
        st.error(f"Error extracting text from image: {e}")
        return None

def extract_text_from_scanned_pdf(pdf_file, start_page, end_page):
    pdf_file.seek(0)  # Reset the file pointer
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    num_pages = len(doc)
    start_page = max(0, start_page - 1)  # Convert to zero-based index
    end_page = min(num_pages - 1, end_page - 1)  # Convert to zero-based index

    extracted_text = ""
    for page_num in range(start_page, end_page + 1):
        page = doc[page_num]
        images = page.get_images()  # Get all images on the page

        for img in images:
            xref = img[0]  # Image XREF
            base_image = doc.extract_image(xref)  # Extract the image
            image = Image.open(io.BytesIO(base_image["image"]))

            # Correctly pass the image to extract_text_from_image
            extracted_text += extract_text_from_image(image) + "\n"
        
        if not images:  # No images found on the page
            extracted_text += "Unable to extract image from page " + str(page_num + 1) + "\n"

    doc.close()  # Close the document
    return extracted_text

# Streamlit app
st.title("Copy Pasta 🍝")
st.subheader("No more painful text (mobile) highlighting. Copy text from long articles with a few clicks")
st.write("This is a simple app that copies text from the upload files or URL so that it is easier to copy large amount of text for prompting. It is not a LLM")
st.write("""
1) Enter a URL or upload a PDF or Image
2) Extract the text 
3) Add prefix (prompt) if you want to use it for prompting (use mine if you want to for summary)
""")

# Option to choose between URL, PDF, and Image
option = st.radio("Choose input type:", ("URL", "PDF", "Image"))

if option == "PDF":
    pdf_file = st.file_uploader("Upload a PDF file", type="pdf")
    
    if pdf_file:
        all_pages = st.checkbox("OCR all pages")
        
        if not all_pages:
            start_page = st.number_input("Starting Page Number", min_value=1, step=1)
            end_page = st.number_input("Ending Page Number", min_value=1, step=1)
            
            if st.button("Extract Text from PDF"):
                if start_page and end_page:
                    if start_page > end_page:
                        start_page, end_page = end_page, start_page
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Try extracting text directly first
                    main_text = extract_text_from_pdf(pdf_reader, start_page, end_page)
                    if main_text.strip() == "":  # Check if extracted text is empty
                        st.warning("No text found in PDF pages. Attempting OCR on scanned pages.")
                        main_text = extract_text_from_scanned_pdf(pdf_file, start_page, end_page)
                    st.session_state['main_text'] = main_text
                    st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
                    # display_pdf_pages(pdf_file, start_page, end_page)  # Display the selected pages
                else:
                    st.error("Please enter valid page numbers.")
        else:
            if st.button("Extract Text from PDF"):
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Try extracting text directly first
                main_text = extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
                if main_text.strip() == "":  # Check if extracted text is empty
                    st.warning("No text found in PDF pages. Attempting OCR on scanned pages.")
                    main_text = extract_text_from_scanned_pdf(pdf_file, 1, len(pdf_reader.pages))
                st.session_state['main_text'] = main_text
                st.session_state['main_text_with_prefix'] = main_text  # Initialize with the original text
                # display_pdf_pages(pdf_file, 1, len(pdf_reader.pages))  # Display all pages

elif option == "URL":
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

elif option == "Image":
    image_file = st.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])
    if image_file:
        if st.button("Extract Text from Image"):
            extracted_text = extract_text_from_image(image_file)
            if extracted_text:
                st.session_state['main_text'] = extracted_text
                st.session_state['main_text_with_prefix'] = extracted_text

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