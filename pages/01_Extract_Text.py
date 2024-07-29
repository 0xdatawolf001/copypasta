import streamlit as st
from bs4 import BeautifulSoup
import requests
import re
from st_copy_to_clipboard import st_copy_to_clipboard
import PyPDF2
import numpy as np
import io
import base64
from easyocr import Reader
import cv2
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from youtube_transcript_api import YouTubeTranscriptApi
import toml
from urllib.parse import urlparse, parse_qs # Add for improved YouTube parsing

# Function to extract YouTube video ID from URL (Improved)
def extract_video_id(url):
    # Define regex patterns for different YouTube URL formats
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/|.+\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:playlist\?list=|watch\?v=)([a-zA-Z0-9_-]{11})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Fallback to parsing query parameters if regex fails
    query = urlparse(url).query
    params = parse_qs(query)
    if 'v' in params:
        return params['v'][0]

    return None

# Function to extract transcript from a YouTube video
def extract_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([d['text'] for d in transcript_list])
        return transcript
    except Exception as e:
        st.error(f"Error extracting YouTube transcript: {e}")
        return None

@st.cache_resource
def load_easyocr_model():
    return Reader(['en'], gpu=False)
reader = load_easyocr_model()

# Function to extract main body text from a URL
def extract_text_from_url(url):
    response = requests.get(url, stream=True) 
    content_type = response.headers.get('Content-Type')
    
    if 'application/pdf' in content_type:
        # If the URL points to a PDF, extract text from the PDF
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
    elif content_type in ['image/png', 'image/jpeg', 'image/jpg']:
        # Read image data into bytes
        image_bytes = response.content 
        return extract_text_from_image(image_bytes) 
    else:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find collapsed sections (often using CSS class "mw-collapsed") 
        for collapsed_section in soup.find_all(class_="mw-collapsed"):
            # Remove the "collapsed" class to expand the section
            collapsed_section['class'] = [cls for cls in collapsed_section['class'] if cls != 'mw-collapsed'] 

        # Extract text after expanding sections
        text = soup.get_text(separator=' ', strip=True)
        cleaned_text = re.sub(r'\s+', ' ', text) 
        return cleaned_text

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_reader, start_page, end_page):
    num_pages = len(pdf_reader.pages)
    start_page = max(0, start_page - 1) 
    end_page = min(num_pages - 1, end_page - 1)  
    
    text = ""
    progress_text = st.empty()  # Create an empty element to update progress
    for page_num in range(start_page, end_page + 1):
        # Calculate and display progress
        progress = (page_num - start_page + 1) / (end_page - start_page + 1)
        progress_text.text(f"Progress: {progress:.0%} ({page_num+1}/{end_page+1})") 

        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        
        # Check if extracted text has less than 2 characters
        if len(page_text.strip()) < 2:
            # If less than 2 characters, assume it's an image and use OCR
            ocr_text = extract_text_from_pdf_image(pdf_reader, page_num)
            if ocr_text:
                text += ocr_text + "\n"
        else:
            # If 2 or more characters, use the extracted text
            text += page_text + "\n"
    
    progress_text.empty() # Optional: Clear the progress message
    return text

# Function to extract text from a PDF page image using OCR
def extract_text_from_pdf_image(pdf_reader, page_num):
    with st.spinner(f"Extracting text from page {page_num + 1}..."):
        pdf_page = pdf_reader.pages[page_num]
        pdf_bytes = io.BytesIO()
        pdf_writer = PyPDF2.PdfWriter()
        pdf_writer.add_page(pdf_page)
        pdf_writer.write(pdf_bytes)
        pdf_bytes.seek(0)
        
        # Use PyMuPDF to convert PDF page to image
        doc = fitz.open(stream=pdf_bytes.read(), filetype="pdf")
        page = doc.load_page(0)  # Load the first page
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Downsize the image to reduce memory usage
        image = image.resize((image.width // 1, image.height // 1))
        
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        text = extract_text_from_image(img_byte_arr)
        
        return text

# Function to extract text from an image using PaddleOCR
def extract_text_from_image(image_bytes):
    try:
        with st.spinner("Extracting text from image..."):
            image = Image.open(io.BytesIO(image_bytes))

            # Downsize the image if it's larger than 720p (optional, but recommended)
            if (image.width > 1920 and image.height > 1080) or (image.height > 1920 and image.width > 1080):
                image = image.resize((image.width // 2, image.height // 2))

            # Convert PIL Image to NumPy array 
            image_np = np.array(image) 

            # Perform OCR using PaddleOCR
            result = ocr.ocr(image_np, cls=False)
            extracted_text = ' '.join([line[1][0] for line in result[0]])
            return extracted_text
    except ValueError as e:
        st.error(f"Error extracting text from image: {e}")
        return None



# Global variable to keep track of current LLM key index
current_llm_key_index = 0

def call_llm(copypasta_text):
    global current_llm_key_index 

    # Access the secret using the current index
    llm_key = st.secrets['llm'][f'llm_model_{current_llm_key_index}']

    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        genai.configure(api_key=llm_key)
        reply = model.generate_content(f"{copypasta_text}", safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE})
        reply = reply.text
        # client = OpenAI(
        #     base_url="https://openrouter.ai/api/v1",
        #     api_key=llm_key,
        # )

        # completion = client.chat.completions.create(
        #     extra_headers={
        #         "HTTP-Referer": "copypasta.streamlit.app", # Optional, for including your app on openrouter.ai rankings.
        #         "X-Title": "copypasta", # Optional. Shows in rankings on openrouter.ai.
        #     },
        #     model="meta-llama/llama-3-8b-instruct:free",
        #     messages=[
        #         {
        #             "role": "user",
        #             "content": copypasta_text,
        #         },
        #     ],
        # )

        # reply = completion.choices[0].message.content
        return reply

    except Exception as e:
        print(f"An error occurred: {e}")
        # Rotate to the next key
        current_llm_key_index = (current_llm_key_index % 2) + 1

        # Check if all keys have been exhausted within the except block
        if current_llm_key_index == 1:
            # All keys have been tried, display error message
            st.error("LLM limit reached! Come back another day")
        else:
            # Silently retry with the next key
            return call_llm(copypasta_text)




# Streamlit app
st.title("Copy Pasta 🍝")
st.subheader("Copy text from articles, PDFs, and images for LLM prompting with one click")

st.write("""
1) Enter a URL, upload a PDF or Image
2) Extract the text 
3) Add a prompt if you want to instruct an LLM model
""")

# Option to choose between URL, PDF, and Image
option = st.radio("## Choose input type:", ("Website Links", "PDF", "Image (Multiple Allowed)"))

if option == "Website Links":
    # Input box for URL
    url = st.text_input("Enter the Website Links:")
    
    # Button to extract text
    if st.button("Extract Text"):
        if url:
            # Check if it's a YouTube link
            video_id = extract_video_id(url) 
            if video_id:
                with st.spinner("Extracting..."): # Add spinner here
                    main_text = extract_youtube_transcript(video_id)
            else:
                with st.spinner("Extracting..."): # Add spinner here
                    main_text = extract_text_from_url(url)
            
            if main_text:
                st.session_state['main_text'] = main_text
        else:
            st.session_state['main_text'] = "Please enter a valid URL."

elif option == "Image (Multiple Allowed)":
    image_files = st.file_uploader("Upload one or more image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if image_files:
        if st.button("Extract Text from Images"):
            with st.spinner("Extracting..."):
                st.markdown("May be slow. Please be patient")
                extracted_text = ""
                progress_text = st.empty()  # Create an empty element to update progress
                for i, image_file in enumerate(image_files):
                    # Calculate and update progress
                    progress = (i + 1) / len(image_files)
                    progress_text.text(f"Progress: {progress:.0%} ({i+1}/{len(image_files)})")
                    extracted_text += extract_text_from_image(image_file.read()) + "\n\n"
                if extracted_text:
                    st.session_state['main_text'] = extracted_text.strip()
                    progress_text.empty() # Optional: Clear the progress message

elif option == "PDF":
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
                    with st.spinner("Extracting..."): # Add spinner here
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        main_text = extract_text_from_pdf(pdf_reader, start_page, end_page)
                        st.session_state['main_text'] = main_text
                else:
                    st.error("Please enter valid page numbers.")
        else:
            if st.button("Extract Text from PDF"):
                with st.spinner("Extracting..."): # Add spinner here
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    main_text = extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
                    st.session_state['main_text'] = main_text

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
    st_copy_to_clipboard(st.session_state['main_text_with_prefix'], "Copy Extracted Text")
elif 'main_text' in st.session_state:
    st_copy_to_clipboard(st.session_state['main_text'], "Copy Extracted Text")

st.write("""
         App is a little slow. Your patience (and support) is appreciated!
         This is a simple app that copies everything on the page so that it is easier to copy large amount of text for prompting on Mobile
         """)
