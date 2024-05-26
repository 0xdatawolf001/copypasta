import streamlit as st

st.title("Welcome to Copy Pasta 🍝")
st.write("""
         This is where you can extract text, copy them, and then use it for LLM prompting.
         
         I created this because its much easier to copy text at a go (copy to clipboard) as opposed to manually highlighting with your finger on the phone

         Here are some pages that you may enjoy. This project is just a pet project I did hastily on the weekends. 

         There are 2 tabs:
         1. **Extract Text** allows you extract text from various media types: PDFs, websites, youtube, and images
         2. **Marketing Prompts** allows you to take that extracted text and pass it into some pre-written marketing prompts that I wrote that can hopefully help you summarize complex writing into more business friendly terms

         My Twitter account is: 0xDataWolf. Let me know if you have any problems or questions and I'll try to help

         Let's go!
         """)

st.subheader("Some recommended LLMs")
st.write("""
         You can try:

         -- labs.perplexity.ai

         -- aistudio.google.com

        for free models that takes in a lot of text
         """)