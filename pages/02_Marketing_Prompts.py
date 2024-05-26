import streamlit as st
from bs4 import BeautifulSoup
import requests
import re
from st_copy_to_clipboard import st_copy_to_clipboard
import PyPDF2
import io
import base64
from easyocr import Reader
import fitz  # PyMuPDF
import os
from PIL import Image
from youtube_transcript_api import YouTubeTranscriptApi
import toml
from urllib.parse import urlparse, parse_qs # Add for improved YouTube parsing
from openai import OpenAI

# # Function to read the API key from secrets.toml
# def get_api_key(file_path="notes.toml"):
#     with open(file_path, "r") as f:
#         config = toml.load(f)
#     return config["api_keys"]["youtube"]

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
    response = requests.get(url)
    content_type = response.headers.get('Content-Type')
    
    if 'application/pdf' in content_type:
        # If the URL points to a PDF, extract text from the PDF
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
    elif 'image' in content_type:
        # If the URL points to an image, extract text from the image
        image_file = io.BytesIO(response.content)
        return extract_text_from_image(image_file)
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
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
        else:
            # If no text is found, convert the page to an image and use OCR
            ocr_text = extract_text_from_pdf_image(pdf_reader, page_num)
            if ocr_text:
                text += ocr_text + "\n"
    
    return text

# Function to extract text from a PDF page image using OCR
def extract_text_from_pdf_image(pdf_reader, page_num):
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
    image = image.resize((image.width // 2, image.height // 2))
    
    # Convert image to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    text = extract_text_from_image(img_byte_arr)
    
    return text

# Function to extract text from an image using EasyOCR
def extract_text_from_image(image_bytes):
    reader = Reader(['en'], gpu=False) # change language if needed
    try:
        result = reader.readtext(image_bytes)
        extracted_text = '\n'.join([text[1] for text in result])
        return extracted_text
    except ValueError as e:
        st.error(f"Error extracting text from image: {e}")
        return None
    
def call_llm(copypasta_text):

    # script_dir = os.path.dirname(__file__)
    # file_path = os.path.join(script_dir, 'notes.toml')

    # parsed_toml = toml.load(file_path)

    # Access the secret
    llm_key =  st.secrets['llm']['llm_model']

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=llm_key,
    )

    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "copypasta.streamlit.app", # Optional, for including your app on openrouter.ai rankings.
            "X-Title": "copypasta", # Optional. Shows in rankings on openrouter.ai.
        },
        model="meta-llama/llama-3-8b-instruct:free",
        messages=[
            {
                "role": "user",
                "content": copypasta_text,
            },
        ],
    )

    reply = completion.choices[0].message.content
    return reply

# Streamlit app
st.title("Marketing Prompts 🤔")
st.subheader("Extract text and run through an LLM that is prompted to help breakdown concepts and ideate copy writing")

st.write("""
1) Enter a URL, upload a PDF or Image
2) Extract the text 
3) Select prompt type
4) See output
""")

# Option to choose between URL, PDF, and Image
option = st.radio("## Choose input type:", ("Website Links", "PDF", "Image (Multiple Allowed)"))

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
                    main_text = extract_text_from_pdf(pdf_reader, start_page, end_page)
                    st.session_state['main_text_2'] = main_text
                else:
                    st.error("Please enter valid page numbers.")
        else:
            if st.button("Extract Text from PDF"):
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                main_text = extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
                st.session_state['main_text_2'] = main_text

elif option == "Website Links":
    # Input box for URL
    url = st.text_input("Enter the Website Links:")
    
    # Button to extract text
    if st.button("Extract Text"):
        if url:
            # Check if it's a YouTube link
            video_id = extract_video_id(url) 
            if video_id:
                main_text = extract_youtube_transcript(video_id)
            else:
                main_text = extract_text_from_url(url)
            
            if main_text:
                st.session_state['main_text_2'] = main_text
        else:
            st.session_state['main_text_2'] = "Please enter a valid URL."

elif option == "Image (Multiple Allowed)":
    image_files = st.file_uploader("Upload one or more image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if image_files:
        if st.button("Extract Text from Images"):
            st.markdown("May be slow. Please be patient")
            extracted_text = ""
            for image_file in image_files:
                extracted_text += extract_text_from_image(image_file.read()) + "\n\n"
            if extracted_text:
                st.session_state['main_text_2'] = extracted_text.strip()

# Define placeholder options for the select box
prompt_options = {
    "Edit for easier reading": "Edit formatting, grammar and punctuation, do not edit/change style, tone, and content. Paragraph accordingly if needed. Retain expletives and vulgarity. This is a scraped page so some words may be transcribed wrongly. Write it neatly in paragraphs so that it is easier to read. Extract the key informative insights. Let each paragraphs be in proper sentences so that it reads off more smoothly. The start of the sentence acts as a takeaway and it should be bolded for easier reading and skimming. Make sure it is informative.   The format and template output should look like this:   **One liner lead sentence that acts like a main takeaway of a point:** Details from the content. Be as complete and comprehensive as possible. Do not lose information.  **Another One liner lead sentence that acts like a main takeaway of a point:** Details from the content. Be as complete and comprehensive as possible. Do not lose information.  So on until ALL informative insights are rewritten and extracted  Avoid adding your own analysis.",
    "Summarize": "Extract the key insights and takeaways. Write in point form and organize section in headers. make sure it is comprehensive and complete and you don’t lose out important information. At the end, have a call to action on the next steps based on what the write up suggest",
    "Write Value Proposition Statements": "Looking at the information above. Fill in the details from the text above with each section with what the user is trying to do. Identify multiple users and multiple use case by user:  1. A user  2. What are they trying to do (first identify the user; start with the phrase “they are trying to [their end goal or jobs to be done]) 3. How they are doing it (current flawed or less superior older way; start with the word “by”) 4. Problem (blocker of progress; to be addressed by benefit later; start with “which leads to...” Usually deterioration on something described with a adverb or adjective) 5. Limitation of current way (addressed by product capability; start with the word “because…” the reason and root cause of the problem caused by a specific step in the current way. Be specific and descriptive here! ) 6. Product capability (addresses limitation of current way; start with the phrase “now you can…” a descriptive activity that the solutions enable to address points in limitation of current way) 7. Product feature (few words on what the capability is called. Start with the word “using”. Also explain how it works and steps it performs to achieve the capability. Be very detailed step by step) 8. Benefit (addresses problem; usually an improvement on something described with an adverb or adjective; starts with the phrase so that [the user]…) 9. Add a section: Why do this (this is how it contributes to their use case; start with the phrase “in order to”)  ",
    "Creating or Caputuring Demand Statements": "Pretend you are an experienced product marketer good at copy writing. Look at the above text. Glossary of terms: Who are the users or persona? What is the current way of doing things? (Addressed by product capability) What is the limitation of the current way (the actual manifestation of the limitation of the current way. Addressed by product feature). What is the core problem? (Implications from limitations of the current way. Has an adjective to describe the pain point: slower xyz, more expensive xyz. Addressed by Benefits later). What is the proposed solution.  What are the features? (What powers this new way.) What are the capabilities of this feature (how they would use the product.) What are the benefits of this feature (the change in state that comes from the solution. Usually an adjective like faster/improved xyz. The result of doing it your way) What is the use case.  A use case is defined as something that addresses all and each of the above listed user+problem with a feature+capability+benefit that you mentioned.  Create 3 messages each under two categories: Demand creation and demand capture messages. The components of a demand creation message are as followed: it contains a use case, current way, limitation of current way and problem. So main hook: Scheduling your meetings by (use case) coordinating over email? (current way) Subhook: Here is how much time you’re wasting every week (problem) sending your availability back and forth (limitation of current way). As for demand capture message it contains another 4 parts: The product capability, feature, benefit, product capability. So main hook: Schedule your meetings (product capability) with a single message (benefit) Sub hook: Calendly is a scheduling tool (product capability) that embeds your availability into a shareable webpage. Note: add the category tag inside the 3 hooks so that I can understand how you are breaking it down. Hooks must be targeted for a different MECE users/persona ",
    "Messaging Based On Problem/Solution Awareness (and how to gain trust)": "I want to write some messaging for the above feature or task that I want you to think off to help me get started on my endeavours.  ``` There are two major categories: Creating demand and capturing Demand  For creating demand there are another 2 stages of awareness: For Problem unaware, lead with an alternative to the current way of doing things. Then Earn trust by showing that we understand their problems and pain point to convince them that they have a problem  For problem aware, lead with the problem statement. Earn trust by showing that we understand the problem and to convince them that they are missing a key capability  As for capturing demand, there is another 2 stages of awareness: For solution aware, lead of capability which is the product’s ability to solve their pain point and problem. We earn their trust that we know and understand what is the excepted capability that comes from our product. And it is convince them that our feature unlocks the capability  As for product aware, we lead with the feature. We earn their trust by connecting their desired features to an outcome. This is to convince them that our solution delivers on its benefit ```   For each type of awareness, show an example ",
    "Things to do based on Customer Maturity": "This is to help me understand the different perspective on where the customer is at by simulating who and what are the customer is thinking based on the phases below. Give some suggests on the content needed to be produced to approach them Market Push Unaware Problem unaware (can you convince them they have a problem) Unaware The aren’t aware of their desire or their need to solve the problem, or they just won’t admit it Content: Educate on trends and the problem such as using white papers, industry reports, trend analysis Problem aware (Can you convince them a solution exists) They know they haven a problem to solve, but aren’t aware of the specific solutions. Content: educate on how to approach the problem. Use frameworks, guides, breakdowns Solution aware (can you convince them your solution is believable) They know their’s is a solution to their problem but they don’t know any specific products to solve it. Content: Show success stories that highlight main capabilities. Use case studies, gain calculations, buying guides Market Pull [Can also be applied to solution aware] Product aware (can you convince them your solution is better than the alternatives) They know your product exists but aren’t completely aware of what it does - or aren’t convinced of how well it does it Content; Pull them in to value creating steps using free trials, consults, value adds Most aware (Can you convince them to buy your solution) They know your product and what it does but haven’t gotten around to purchasing yet", 
    "Jobs To Be Done": "What are the jobs to be done of entity, person, or persona above? Write in the context of the universal job map (Define, Locate, Prepare, Confirm, Execute, Monitor, Modify, Conclude) outlined by Anthony Ulwick from his Outcome driven innovation framework). Title each job stage on the map with a broader jobs to be done statement. Identify 5 tasks under each job stage. Write the desired outcome statement as well for every task. The jobs to be done statement that follows the format of the verb+object+context clarifier. Note that the jobs to be done should be solution free or doesn’t assume a solution but an actual task the job performer wants solved, timeless, no requirements or specifications. Remember: we are not stating what they are doing, we are saying what they are trying to accomplish. Think checkpoints along the way in getting the job done. Then, write the desired outcome statement with the format of (minimize or maximize + measurable metric that the job performer gauges performance of the quality of job getting done + the object that the job performer can influence + the context clarifier). It should be one full sentence.   ",
    "What Changes Customer Habits?": "Fill in the content from above into the template below: 1. Push & Pull: Push: What external (e.g., societal shifts, new responsibilities) and internal (e.g., frustrations, aspirations) factors are driving users to seek change? Example: Having a second child makes grocery shopping difficult, pushing parents towards easier solutions. An entrepreneur feeling stuck seeks solutions to improve their business. Pull: What positive outcomes do users envision with a solution, and what features attract them? Example: Parents desire smoother grocery shopping to spend more time with their children. Flexible delivery options attract users to grocery delivery services. 2. Anxiety & Habit: Anxiety: What uncertainties (anxiety-in-choice) and concerns (anxiety-in-use) do users have about the product? Example: Users worry if a business coaching service makes them appear inexperienced. Users feel anxious about inconsistent bus arrival times. Habit: What routines (habit-in-choice) and ingrained practices (habit-in-use) prevent users from switching? Example: Users accustomed to specific spreadsheet software hesitate to switch. Shopping for groceries on a whim hinders adapting to meal planning for delivery services.",
    "Blue Ocean Non-Customers": "Explore the business using the Blue Ocean Strategy’s 3 tiers of noncustomers consist of: First-Tier Non-Customers: These are the closest to your market. They minimally purchase your industry’s offerings out of necessity but are ready to switch as soon as they find a superior alternative. To attract these non-customers, you need to understand their needs and pain points and offer a better solution. Second-Tier Non-Customers: These are people who consciously refuse your market’s offerings. They have recognized your industry but have chosen not to participate. To attract these non-customers, you need to understand their reasons for refusal and address these issues in your offerings. Third-Tier Non-Customers: These are the furthest from your market. They have never considered your industry’s offerings as an option. These non-customers represent a significant opportunity as they have often been overlooked by your industry. To attract these non-customers, you need to understand their needs and how your offerings could potentially meet those needs.  Be comprehensive, creative, and think critically on the various wide range of type of user. This exercise is to expand to new customers. Identify more than 10 user type or persona per tier. Propose what painpoints, needs , and customer’s jobs to be done that they need to do per user type   ",
    "Product Requirement Doc": "Write a product requirement documentation. Add on milestones, roadmap and prioritize starting from items that are foundational to do other bigger things or because they are low hanging fruits that we can achieve to get something out. Justify your suggested roadmap and milestone "
}

# Select box for prompt options
selected_option = st.selectbox("Select a prompt option:", list(prompt_options.keys()))

# Display the selected prompt and extracted text
if 'main_text_2' in st.session_state:
    st.subheader("Extracted Text:")
    st.text_area("No editing for security reasons. Copy and paste your own text from Extract Text and use your LLM of choice for custom prompts", st.session_state['main_text_2'], height=300, disabled=True) # Disable editing

    st.write("""
         This feeds the extracted text to OpenRouter's Llama 8b! Can be a little slow. Thank you for waiting
         """)
    
    st.write(f"""
         There are {len(st.session_state['main_text_2'])} characters. Page Count: {(len(st.session_state['main_text_2']) // 16000)+1}
         """)
    
    # Button to send combined text to LLM
    if st.button("Send to LLM (Max first 10 pages)"):
        combined_text = f"{st.session_state['main_text_2']}\n\n{prompt_options[selected_option]}"

        # Chunking logic
        chunk_size = 16000
        chunks = [combined_text[i:i + chunk_size] for i in range(0, len(combined_text), chunk_size)]

        # Display a message with character count and update it dynamically
        processing_message = st.empty()
        processing_message.text(f"Processing your text: {len(combined_text)} characters")

        llm_response = ""
        for i, chunk in enumerate(chunks):
            processing_message.text(f"Processing chunk {i+1}/{len(chunks)}...")
            llm_response += f"\n\n# Page {i+1}\n" + call_llm(f"{chunk}\n\n{prompt_options[selected_option]}")
            # Add a horizontal rule (---) after each page
            if i < len(chunks) - 1: 
                llm_response += "\n\n---\n\n"

        # Update the message to "Done!" after LLM response is received
        processing_message.text("Done!")

        # Display the LLM response
        st.subheader("LLM Response:")
        st.markdown(llm_response)
        st_copy_to_clipboard(llm_response, "Copy LLM Answer")
