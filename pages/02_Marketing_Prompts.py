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
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from youtube_transcript_api import YouTubeTranscriptApi
import toml
from urllib.parse import urlparse, parse_qs  # Add for improved YouTube parsing


# Function to extract YouTube video ID from URL (Improved)
def extract_video_id(url):
    # Define regex patterns for different YouTube URL formats
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/|.+\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:playlist\?list=|watch\?v=)([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Fallback to parsing query parameters if regex fails
    query = urlparse(url).query
    params = parse_qs(query)
    if "v" in params:
        return params["v"][0]

    return None


# Function to extract transcript from a YouTube video
def extract_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([d["text"] for d in transcript_list])
        return transcript
    except Exception as e:
        st.error(f"Error extracting YouTube transcript: {e}")
        return None


@st.cache_resource
def load_easyocr_model():
    return Reader(["en"], gpu=False)


reader = load_easyocr_model()


# Function to extract main body text from a URL
def extract_text_from_url(url):
    response = requests.get(url, stream=True)
    content_type = response.headers.get("Content-Type")

    if "application/pdf" in content_type:
        # If the URL points to a PDF, extract text from the PDF
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return extract_text_from_pdf(pdf_reader, 1, len(pdf_reader.pages))
    elif content_type in ["image/png", "image/jpeg", "image/jpg"]:
        # Read image data into bytes
        image_bytes = response.content
        return extract_text_from_image(image_bytes)
    else:
        soup = BeautifulSoup(response.content, "html.parser")

        # Find collapsed sections (often using CSS class "mw-collapsed")
        for collapsed_section in soup.find_all(class_="mw-collapsed"):
            # Remove the "collapsed" class to expand the section
            collapsed_section["class"] = [
                cls for cls in collapsed_section["class"] if cls != "mw-collapsed"
            ]

        # Extract text after expanding sections
        text = soup.get_text(separator=" ", strip=True)
        cleaned_text = re.sub(r"\s+", " ", text)
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

    progress_text.empty()  # Optional: Clear the progress message
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
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        text = extract_text_from_image(img_byte_arr)

        return text


# Function to extract text from an image using PaddleOCR
def extract_text_from_image(image_bytes):
    try:
        with st.spinner("Extracting text from image..."):
            image = Image.open(io.BytesIO(image_bytes))

            # Downsize the image if it's larger than 720p (optional, but recommended)
            if (image.width > 1920 and image.height > 1080) or (
                image.height > 1920 and image.width > 1080
            ):
                image = image.resize((image.width // 2, image.height // 2))

            # Convert PIL Image to NumPy array
            image_np = np.array(image)

            # Perform OCR using PaddleOCR
            result = ocr.ocr(image_np, cls=False)
            extracted_text = " ".join([line[1][0] for line in result[0]])
            return extracted_text
    except ValueError as e:
        st.error(f"Error extracting text from image: {e}")
        return None


# Global variable to keep track of current LLM key index
current_llm_key_index = 0


def call_llm(copypasta_text):
    global current_llm_key_index

    # Access the secret using the current index
    llm_key = st.secrets["llm"][f"llm_model_{current_llm_key_index}"]

    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        genai.configure(api_key=llm_key)
        reply = model.generate_content(
            f"{copypasta_text}",
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
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
st.title("Marketing Prompts 🤔")
st.subheader(
    "Extract text and run through an LLM that is prompted to help breakdown concepts and ideate copy writing"
)

st.write(
    """
1) Enter a URL, upload a PDF or Image
2) Extract the text 
3) Select prompt type
4) See output
"""
)

# Option to choose between URL, PDF, and Image
option = st.radio(
    "## Choose input type:", ("Website Links", "PDF", "Image (Multiple Allowed)")
)

if option == "Website Links":
    # Input box for URL
    url = st.text_input("Enter the Website Links:")

    # Button to extract text
    if st.button("Extract Text"):
        if url:
            # Check if it's a YouTube link
            video_id = extract_video_id(url)
            if video_id:
                with st.spinner("Extracting..."):  # Add spinner here
                    main_text = extract_youtube_transcript(video_id)
            else:
                with st.spinner("Extracting..."):  # Add spinner here
                    main_text = extract_text_from_url(url)

            if main_text:
                st.session_state["main_text_2"] = main_text
        else:
            st.session_state["main_text_2"] = "Please enter a valid URL."

elif option == "Image (Multiple Allowed)":
    image_files = st.file_uploader(
        "Upload one or more image files",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )
    if image_files:
        if st.button("Extract Text from Images"):
            with st.spinner("Extracting..."):
                st.markdown("May be slow. Please be patient")
                extracted_text = ""
                progress_text = st.empty()  # Create an empty element to update progress
                for i, image_file in enumerate(image_files):
                    # Calculate and update progress
                    progress = (i + 1) / len(image_files)
                    progress_text.text(
                        f"Progress: {progress:.0%} ({i+1}/{len(image_files)})"
                    )
                    extracted_text += (
                        extract_text_from_image(image_file.read()) + "\n\n"
                    )
                if extracted_text:
                    st.session_state["main_text_2"] = extracted_text.strip()
                    progress_text.empty()  # Optional: Clear the progress message

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
                    with st.spinner("Extracting..."):  # Add spinner here
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        main_text = extract_text_from_pdf(
                            pdf_reader, start_page, end_page
                        )
                        st.session_state["main_text_2"] = main_text
                else:
                    st.error("Please enter valid page numbers.")
        else:
            if st.button("Extract Text from PDF"):
                with st.spinner("Extracting..."):  # Add spinner here
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    main_text = extract_text_from_pdf(
                        pdf_reader, 1, len(pdf_reader.pages)
                    )
                    st.session_state["main_text_2"] = main_text

# Define placeholder options for the select box
prompt_options = {
    "Summarize": "Extract the key insights and takeaways. Write in point form and organize section in headers. make sure it is comprehensive and complete and you don't lose out important information. If possible, talk about implications and call to actions as well. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Editing": "Format the extracted text nicely so its easier to read. Avoid changing content. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Find Value Proposition": "Looking at the information above. Fill in the details from the text above with each section with what the user is trying to do. Identify multiple users and multiple use case by user:  1. A user  2. What are they trying to do (first identify the user; start with the phrase “they are trying to [their end goal or jobs to be done]) 3. How they are doing it (current flawed or less superior older way; start with the word “by”) 4. Problem (blocker of progress; to be addressed by benefit later; start with “which leads to...” Usually deterioration on something described with a adverb or adjective) 5. Limitation of current way (addressed by product capability; start with the word “because…” the reason and root cause of the problem caused by a specific step in the current way. Be specific and descriptive here! ) 6. Product capability (addresses limitation of current way; start with the phrase “now you can…” a descriptive activity that the solutions enable to address points in limitation of current way) 7. Product feature (few words on what the capability is called. Start with the word “using”. Also explain how it works and steps it performs to achieve the capability. Be very detailed step by step) 8. Benefit (addresses problem; usually an improvement on something described with an adverb or adjective; starts with the phrase so that [the user]…) 9. Add a section: Why do this (this is how it contributes to their use case; start with the phrase “in order to”). Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Creating/Caputuring Demand": "Pretend you are an experienced product marketer good at copy writing. Look at the above text. Glossary of terms: Who are the users or persona? What is the current way of doing things? (Addressed by product capability) What is the limitation of the current way (the actual manifestation of the limitation of the current way. Addressed by product feature). What is the core problem? (Implications from limitations of the current way. Has an adjective to describe the pain point: slower xyz, more expensive xyz. Addressed by Benefits later). What is the proposed solution.  What are the features? (What powers this new way.) What are the capabilities of this feature (how they would use the product.) What are the benefits of this feature (the change in state that comes from the solution. Usually an adjective like faster/improved xyz. The result of doing it your way) What is the use case.  A use case is defined as something that addresses all and each of the above listed user+problem with a feature+capability+benefit that you mentioned.  Create 3 messages each under two categories: Demand creation and demand capture messages. The components of a demand creation message are as followed: it contains a use case, current way, limitation of current way and problem. So main hook: Scheduling your meetings by (use case) coordinating over email? (current way) Subhook: Here is how much time you're wasting every week (problem) sending your availability back and forth (limitation of current way). As for demand capture message it contains another 4 parts: The product capability, feature, benefit, product capability. So main hook: Schedule your meetings (product capability) with a single message (benefit) Sub hook: Calendly is a scheduling tool (product capability) that embeds your availability into a shareable webpage. Note: add the category tag inside the 3 hooks so that I can understand how you are breaking it down. Hooks must be targeted for a different MECE users/persona. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Copy depending on Problem/Solution Awareness": "I want to write some messaging for the above feature or task that I want you to think off to help me get started on my endeavours.  ``` There are two major categories: Creating demand and capturing Demand  For creating demand there are another 2 stages of awareness: For Problem unaware, lead with an alternative to the current way of doing things. Then Earn trust by showing that we understand their problems and pain point to convince them that they have a problem  For problem aware, lead with the problem statement. Earn trust by showing that we understand the problem and to convince them that they are missing a key capability  As for capturing demand, there is another 2 stages of awareness: For solution aware, lead of capability which is the product's ability to solve their pain point and problem. We earn their trust that we know and understand what is the excepted capability that comes from our product. And it is convince them that our feature unlocks the capability  As for product aware, we lead with the feature. We earn their trust by connecting their desired features to an outcome. This is to convince them that our solution delivers on its benefit ```   For each type of awareness, show an example. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content ",
    "Actionables based on Customer Maturity": "This is to help me understand the different perspective on where the customer is at by simulating who and what are the customer is thinking based on the phases below. Give some suggests on the content needed to be produced to approach them Market Push Unaware Problem unaware (can you convince them they have a problem) Unaware The aren't aware of their desire or their need to solve the problem, or they just won't admit it Content: Educate on trends and the problem such as using white papers, industry reports, trend analysis Problem aware (Can you convince them a solution exists) They know they haven a problem to solve, but aren't aware of the specific solutions. Content: educate on how to approach the problem. Use frameworks, guides, breakdowns Solution aware (can you convince them your solution is believable) They know their's is a solution to their problem but they don't know any specific products to solve it. Content: Show success stories that highlight main capabilities. Use case studies, gain calculations, buying guides Market Pull [Can also be applied to solution aware] Product aware (can you convince them your solution is better than the alternatives) They know your product exists but aren't completely aware of what it does - or aren't convinced of how well it does it Content; Pull them in to value creating steps using free trials, consults, value adds Most aware (Can you convince them to buy your solution) They know your product and what it does but haven't gotten around to purchasing yet. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Jobs To Be Done": "What are the jobs to be done of entity, person, or persona above? Write in the context of the universal job map (Define, Locate, Prepare, Confirm, Execute, Monitor, Modify, Conclude) outlined by Anthony Ulwick from his Outcome driven innovation framework). Title each job stage on the map with a broader jobs to be done statement. Identify 5 tasks under each job stage. Write the desired outcome statement as well for every task. The jobs to be done statement that follows the format of the verb+object+context clarifier. Note that the jobs to be done should be solution free or doesn't assume a solution but an actual task the job performer wants solved, timeless, no requirements or specifications. Remember: we are not stating what they are doing, we are saying what they are trying to accomplish. Think checkpoints along the way in getting the job done. Then, write the desired outcome statement with the format of (minimize or maximize + measurable metric that the job performer gauges performance of the quality of job getting done + the object that the job performer can influence + the context clarifier). It should be one full sentence. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "What Changes Customer Habits?": "Fill in the content from above into the template below: 1. Push & Pull: Push: What external (e.g., societal shifts, new responsibilities) and internal (e.g., frustrations, aspirations) factors are driving users to seek change? Example: Having a second child makes grocery shopping difficult, pushing parents towards easier solutions. An entrepreneur feeling stuck seeks solutions to improve their business. Pull: What positive outcomes do users envision with a solution, and what features attract them? Example: Parents desire smoother grocery shopping to spend more time with their children. Flexible delivery options attract users to grocery delivery services. 2. Anxiety & Habit: Anxiety: What uncertainties (anxiety-in-choice) and concerns (anxiety-in-use) do users have about the product? Example: Users worry if a business coaching service makes them appear inexperienced. Users feel anxious about inconsistent bus arrival times. Habit: What routines (habit-in-choice) and ingrained practices (habit-in-use) prevent users from switching? Example: Users accustomed to specific spreadsheet software hesitate to switch. Shopping for groceries on a whim hinders adapting to meal planning for delivery services. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Finding Non-Customers": "Explore the business using the Blue Ocean Strategy's 3 tiers of noncustomers consist of: First-Tier Non-Customers: These are the closest to your market. They minimally purchase your industry's offerings out of necessity but are ready to switch as soon as they find a superior alternative. To attract these non-customers, you need to understand their needs and pain points and offer a better solution. Second-Tier Non-Customers: These are people who consciously refuse your market's offerings. They have recognized your industry but have chosen not to participate. To attract these non-customers, you need to understand their reasons for refusal and address these issues in your offerings. Third-Tier Non-Customers: These are the furthest from your market. They have never considered your industry's offerings as an option. These non-customers represent a significant opportunity as they have often been overlooked by your industry. To attract these non-customers, you need to understand their needs and how your offerings could potentially meet those needs.  Be comprehensive, creative, and think critically on the various wide range of type of user. This exercise is to expand to new customers. Identify more than 10 user type or persona per tier. Propose what painpoints, needs , and customer's jobs to be done that they need to do per user type. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Product Requirement Doc": "Looking at the above content pretend You are the product manager responsible for a new module/feature being developed for your product based on the above content. The module aims to enhance the user experience and add valuable functionality to the existing product. You have conducted user research, gathered user feedback, and analyzed market trends to inform the development of this module. Based on your findings, the module is intended to address a specific pain point that users have been facing, providing a solution that will significantly improve their workflow efficiency. The module should seamlessly integrate with the existing product, enhancing its capabilities and delivering a cohesive user experience. In terms of target users, the module should cater to a specific segment of your user base. These users have specific characteristics, needs, and goals that the module should address. Create user stories that clearly illustrate how the module meets their requirements and solves their problems. To ensure clarity and actionable development, outline the specific features and functionalities that the module should have. These should be detailed, yet easily understandable by both technical and non-technical stakeholders. Break down the requirements into granular tasks or user stories that can be assigned to the development team. Consider various use cases and scenarios where the module will be utilized. Describe how users will interact with the module in different situations, emphasizing the benefits and value it brings to their workflow. Ensure that the module seamlessly integrates into the overall product ecosystem, enhancing the user experience across all touchpoints. Define the scope of the module clearly, outlining what it will and will not do. Identify any technical or resource limitations that may impact the module's development or usage. This will help manage expectations and ensure that the module aligns with the available resources and timeframe. Specify any performance requirements or scalability considerations for the module. Define benchmarks or metrics to measure its performance, ensuring that it delivers a smooth and efficient user experience. Anticipate usage loads and ensure that the module can handle the expected user base. Provide detailed guidelines and specifications for the module's user interface (UI) and user experience (UX). Consider the existing visual and interaction design patterns of the product to maintain consistency. Include wireframes, mockups, or visual examples to illustrate the desired look and feel of the module. Identify any dependencies or integrations with other modules or systems. Describe how the module should interact with external components, APIs, or databases. Specify any data or security considerations that need to be addressed during development. Define the testing requirements for the module. Specify the expected test coverage, testing methodologies, and any specific quality standards or certifications that need to be met. Consider both functional and non-functional testing to ensure a robust and reliable module. Establish a timeline for the module's development, including key milestones or deliverables. Consider dependencies on other modules or product releases to ensure a cohesive roadmap. This will enable effective planning, resource allocation, and progress tracking. Describe the expected documentation for the module, such as user guides, API documentation, or technical specifications. Consider any support or training materials that may be needed to assist users in understanding and utilizing the module effectively. Lastly, emphasize the importance of feedback and iteration throughout the development process. Encourage stakeholders to provide input and suggestions for improvement. Allow for revisions to the PRD as needed to ensure alignment with stakeholder expectations and continuous improvement of the module. Please ensure that the PRD is comprehensive, clear, concise, and actionable, serving as a valuable reference for the development team and a communication tool for stakeholders. Utilize the provided data and information to create a well-structured and detailed PRD that aligns with the overall product vision. With proper formatting Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content",
    "Hook Template 1": """Looking at the above, fill in some hooks with the template below. The format is template number, pointer header, and an example wrapped in square brackets to help you! You can change the format and text if needed. These are used so that people will be interested to read my stuff Template 1: Credibility statement: [hit 404K impressions & 1,286 followers in July.] Plan: [And I am confident I can reach 10K by the end of 2022.] The Promise: [Here's my plan (feel free to steal)] Template2: General statement: [If you use it right, Google is the most powerful tool in the world.] The "most people" statement: [But the truth is most people suck at it.-] The promise: [Here are 8 Googling tips that you probably don't know] Template 3: Before Transformation: [In 2020, I was anxious, out of shape, and depressed.] After transformation [Since then, I got jacked, traveled the world, hit YouTube monetization. learned German and Chinese. Created a 4-figure monthly ghostwriting business.] What's in it for me: [Here are the 7 Habits that changed my life:] Template 4: Achievement: [I've done $2M in income in 2.5 years as a solopreneur.] The "no effort" statement: [And I didn't write a single line of code.] Listicle start: [My 14 "must use" no-code tools:] Template 5: Common statement: [The most valuable copywriting skill? Storytelling] Why should I care?: [Master it and you'll 10x your income.] Listicle: [These 9 storytelling principles will get you started]. Template 6: Common statement: [The most popular writing advice Edit your work.] What most people don't tell you: [The least common follow-up: How to edit your work.] Credibility statement: [I've edited 3+ million words in 5 years.] The promise: [Here's the process I use to deliver A+ work that meets clients' expectations and converts] Template 7: Story opener: [10 years ago, I broke my neck. Then doctors found a tumour at the base of my skull. And my spine bent by 56 degrees.] Weird statement: [It was the best thing that ever happened.] "What's in it for me?': [Here are 10 life-changing lessons l've learned:] Template 8: Celebrity: [The most creative company of the last 30 years: Pixar.] WHO & WHY should care?:  [Back in 2011, Pixar storyboard artist Emma Coats shared their "22 Rules For Storytelling." And the rules are a must-read for writers, entrepreneurs, and anyone who wants to tell captivating stories.] The promise: [Here's the breakdown:] Template 9: Curiosity Gap: [How to land clients on Twitter with:] Breaks the expectations: [No outreach. No testimonials. No big following.] The promise: [Here's how I did it:] Template 10: Captures attention: [Storytelling 101:] Says "I did the work for you”: [Over the past 6 months, l've studied over 82 threads, 54 articles, 3 books, and countless YouTube videos to master storytelling.] Distillation:  [What I found out? Storytellers use the same 12 frameworks every time:]. Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content""",
    "Hook Template 2": """Looking at the above, fill in some hooks with the template below.  These are used so that people will be interested to read my stuff Template 1: The Personal Story Thread Use this template to share a personal story of transformation or achievement. Describe the challenges you faced, how you overcame them, and the lessons you learned. Template The Personal Story Thread How I went from: {CrappyThing1} {CrappyThing2} {CrappyThing3} To: {Improvement1} {Improvement2} {Improvement3} {Here'sMyStory:} Example At 21: Ruled by fear A slave to my desires Seeing 3am more than 6am More bad habits than Ed Sheeran At 27: Exercising daily Waking up at 5:30am Using fear as a compass Running ultra-marathons Here are 19 rules that changed my life: Template 2: The Celebrity Thread Use this template to share inspiring stories or lessons from famous people. Describe their achievements, and how they can be applied to everyday life. Template The Celebrity Thread {CelebrityFigure} was {HugePositiveStatement}. They did {Accomplishment1, Accomplishment2, Accomplishment3}. Here's their {Secrets, Frameworks, Lessons}: Example {CelebrityFigure} was a self-made billionaire. They did {Accomplishment1, Accomplishment2, Accomplishment3}. Here's their {Secrets, Frameworks, Lessons}: Template 3: The “Most People Suck” Thread Use this template to highlight a common problem or skill that most people struggle with, and offer solutions or tips to improve. Template The “Most People Suck” Thread Most people suck at {Skill}. Here are {OddNumber} ways to {HelpYouNotSuck}: Example Most people suck at writing. Here are 7 ways to improve your writing skills: Template 4: The “How to (with a twist)” Thread Use this template to offer a unique solution or approach to a common problem, with a twist that sets it apart from others. Template The “How to (with a twist)” Thread How to {DesiredOutcome} (without knowing {CommonObjection}) Example How to learn a new language (without knowing how to read). Template 5: The “I Did The Work For You” Thread Use this template to share the results of your research or analysis of someone else's work, and offer actionable insights or takeaways. Template The “I Did The Work For You” Thread {Someone} did {ImpressiveAccomplishment}. I spent {LongHours} studying {TheirProcess}. Here's what I found: Example {Someone} wrote a bestselling book. I spent 10 hours studying their writing process. Here's what I found: Template 6: The “Super Power” Thread Use this template to highlight a valuable skill or trait that can be a game-changer for others, and offer tips or resources to develop it. Template The “Super Power” Thread {Skill} is a superpower. {ButCommonEnemy} does a terrible job teaching {ChosenSkill}. Here are {Number} {Threads/People/Tips/Tools} to {DesiredOutcome}: Example Writing is a superpower. Schools do a terrible job teaching writing. Here are 5 resources to improve your writing skills: Template 7: The List Thread Use this template to share a list of tips, resources, or insights on a specific topic. Template The List Thread Here are {Number} {Threads/People/Tips/Tools} to {DesiredOutcome}: Example Here are 10 productivity hacks to boost your efficiency: Template 8: The Storytelling Thread Use this template to share a engaging story that teaches a lesson or conveys a message. Template The Storytelling Thread {Story} Here's what I learned: Example I once failed a job interview. Here's what I learned from the experience: Template 9: The Expert Thread Use this template to share expert insights or advice on a specific topic, and offer actionable takeaways. Template The Expert Thread {ExpertQuote} Here's what it means for you: Example “Focus on the process, not the outcome.” - {ExpertName} Here's what it means for you:  Focus on the main content and ignore other extra text as this is hastily scraped from a website so it contains other content""",
}

# Select box for prompt options
selected_option = st.selectbox("Select a prompt option:", list(prompt_options.keys()))

# Display the selected prompt and extracted text
if "main_text_2" in st.session_state:
    st.subheader("Extracted Text:")
    st.text_area(
        "No editing for security reasons. Copy and paste your own text from Extract Text and use your LLM of choice for custom prompts",
        st.session_state["main_text_2"],
        height=300,
        disabled=True,
    )  # Disable editing

    st.write(
        """
         This feeds the extracted text to OpenRouter's Llama 8b! Can be a little slow. Thank you for waiting
         """
    )

    st.write(
        f"""
         There are {len(st.session_state['main_text_2'])} characters. Page Count: {(len(st.session_state['main_text_2']) // 30000)+1}
         """
    )

    if st.button("Send to LLM (Max 10 pages)"):
        if selected_option == "Summarize":
            # Apply Editing prompt first for Summarization
            combined_text = (
                f"{st.session_state['main_text_2']}\n\n{prompt_options['Editing']}"
            )

            # Chunking logic
            chunk_size = 30000
            chunks = [
                combined_text[i : i + chunk_size]
                for i in range(0, len(combined_text), chunk_size)
            ]
            chunks = chunks[:10]

            processing_message = st.empty()
            processing_message.text(
                f"Processing your text: {len(combined_text)} characters"
            )

            edited_text = ""
            for i, chunk in enumerate(chunks):
                processing_message.text(f"Processing chunk {i+1}/{len(chunks)}...")
                edited_text += f"\n\n# Page {i+1}\n" + call_llm(f"{chunk}")
                if i < len(chunks) - 1:
                    edited_text += "\n\n---\n\n"

            with st.spinner("Almost Done ..."):
                llm_response = call_llm(
                    f"{edited_text}{prompt_options[selected_option]}"
                )
            st.subheader("LLM Response:")
            st.markdown(llm_response)
            st_copy_to_clipboard(llm_response, "Copy LLM Answer")

        elif selected_option == "Editing":
            # For Editing, process each chunk with the Editing prompt
            chunk_size = 30000
            chunks = [
                st.session_state["main_text_2"][i : i + chunk_size]
                for i in range(0, len(st.session_state["main_text_2"]), chunk_size)
            ]
            chunks = chunks[:10]

            processing_message = st.empty()
            processing_message.text(
                f"Processing your text: {len(st.session_state['main_text_2'])} characters"
            )

            llm_response = ""
            for i, chunk in enumerate(chunks):
                processing_message.text(f"Processing chunk {i+1}/{len(chunks)}...")
                llm_response += f"\n\n# Page {i+1}\n" + call_llm(
                    f"{chunk}\n\n{prompt_options[selected_option]}"
                )
                if i < len(chunks) - 1:
                    llm_response += "\n\n---\n\n"

            processing_message.text("Done!")

            st.subheader("LLM Response:")
            st.markdown(llm_response)
            st_copy_to_clipboard(llm_response, "Copy LLM Answer")

        else:
            # For all other options, use the selected prompt directly
            combined_text = f"{st.session_state['main_text_2']}\n\n{prompt_options[selected_option]}"

            # Chunking logic (same as before)
            chunk_size = 30000
            chunks = [
                combined_text[i : i + chunk_size]
                for i in range(0, len(combined_text), chunk_size)
            ]
            chunks = chunks[:10]

            processing_message = st.empty()
            processing_message.text(
                f"Processing your text: {len(combined_text)} characters"
            )

            llm_response = ""
            for i, chunk in enumerate(chunks):
                processing_message.text(f"Processing chunk {i+1}/{len(chunks)}...")
                llm_response += f"\n\n# Page {i+1}\n" + call_llm(
                    f"{chunk}\n\n{prompt_options[selected_option]}"
                )
                if i < len(chunks) - 1:
                    llm_response += "\n\n---\n\n"

            processing_message.text("Done!")

            st.subheader("LLM Response:")
            st.markdown(llm_response)
            st_copy_to_clipboard(llm_response, "Copy LLM Answer")
