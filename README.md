# Welcome to Copy Pasta 🍝
This is where you can extract text, copy them, and then use it for LLM prompting.
I created this because its much easier to copy text at a go (copy to clipboard) as opposed to manually highlighting with your finger on the phone

Here are some pages that you may enjoy. This project is just a pet project I did hastily on the weekends. 

There are 2 tabs:
  1. **Extract Text** allows you extract text from various media types: PDFs, websites, youtube, and images

  2. **Marketing Prompts** allows you to take that extracted text and pass it into some pre-written marketing prompts that I wrote that can hopefully help you summarize complex writing into more business friendly terms

My Twitter account is: 0xDataWolf. Let me know if you have any problems or questions and I'll try to help

## Copy Pasta 🍝 - Streamline Your LLM Prompting

This Streamlit app simplifies the process of copying large amounts of text from various sources (websites, PDFs, images) for easy pasting into LLM prompts, especially on mobile devices. 

### Features:

- **Extract text from:**
    - Website links (including YouTube transcripts)
    - PDF files (with optional OCR for all or specific pages)
    - Images (multiple image uploads supported)
- **Add a prefix paragraph:** 
    - Include instructions or context for your LLM prompt directly within the app.
    - A default prefix for summarization is provided, which you can customize.
- **Copy to clipboard with one click:** Easily transfer the extracted text (with or without the prefix) to your clipboard for pasting into your LLM tool of choice. 

### How to Use:

1. **Choose your input type:** Select "Website Links", "PDF", or "Image (Multiple Allowed)".
2. **Provide the input:**
    - **Website Links:** Paste the URL into the text box.
    - **PDF:** Upload the PDF file. You can choose to OCR all pages or specify a page range.
    - **Image (Multiple Allowed):**  Upload one or more image files. Note that processing time may be longer for multiple images.
3. **Extract the text:** Click the "Extract Text" button. The extracted text will appear in the "Extracted Text" text area. 
4. **(Optional) Add a prefix:** 
    - Check the "Add Prefix Prompt Paragraph" checkbox.
    - Customize the default prefix or write your own instructions in the "Prefix Text" text area.
    - Click "Refresh with Prefix" to see the combined text.
5. **Copy to clipboard:**
    - Click the "Copy Extracted Text" button. The text (with or without the prefix, depending on your selection) will be copied to your clipboard.

### Notes:

- The app requires an internet connection to function.
- Extracting text from images and PDFs can take some time, especially for larger files. Please be patient.
- This app focuses on text extraction and simple prefix addition. It does not directly interact with any LLM. You will need to paste the copied text into your preferred LLM tool.

### Tips:

- Use the prefix feature to give your LLM clear instructions on what to do with the extracted text. For example, you can ask it to summarize the text, identify key themes, or translate it into another language. 
- Be as specific as possible in your prefix instructions to get the best results from your LLM.

## Marketing Prompts 🤔

This Streamlit app helps you extract text from various sources (websites, PDFs, images), process it using an LLM (currently OpenRouter's Llama 8b), and generate marketing insights based on your chosen prompt.

### Features:

- **Extract text from:**
    - Website links (including YouTube transcripts)
    - PDF files (with optional OCR for all or specific pages)
    - Images (multiple image uploads supported)
- **Process extracted text with an LLM:**
    - Uses OpenRouter's Llama 8b model for powerful text processing.
    - Automatically chunks large texts for efficient handling.
- **Choose from a variety of marketing-focused prompts:**
    - Summarize key insights
    - Edit and format text for readability
    - Find value propositions
    - Create demand creation/capture messages
    - Generate copy based on problem/solution awareness
    - Analyze customer maturity and suggest actionables
    - Identify jobs to be done
    - Understand factors influencing customer habits
    - Explore non-customer segments
    - Create a product requirement document
    - Generate marketing hooks based on different templates

### How to Use:

1. **Choose your input type:** Select whether you want to extract text from a website link, PDF, or images.
2. **Provide the input:**
    - For websites, enter the URL.
    - For PDFs, upload the file and choose whether to OCR all or specific pages.
    - For images, upload one or more image files.
3. **Extract the text:** Click the "Extract Text" button.
4. **Select a prompt option:** Choose the type of marketing insight you want to generate.
5. **Send to LLM:** Click the "Send to LLM" button.
6. **View and copy the LLM response:**  The generated text will appear below, and you can copy it to your clipboard.

### Notes:

- The app requires an internet connection to function.
- Extracting text from PDFs and images can be time-consuming, especially for large files.
- The LLM processing time depends on the length of the text and the complexity of the prompt.
- The app uses OpenRouter's free tier, which may have usage limits.
- The "Editing" prompt is automatically applied before other prompts (except Summarization) to improve the input for the LLM.

### Future Enhancements:

- Add more prompt options.
- Allow users to input their own custom prompts.
- Integrate with other LLMs.
- Improve the user interface and user experience. 
