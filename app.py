import streamlit as st
import requests
import base64
from PIL import Image
import io
import os
from openai import OpenAI

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def perform_ocr(image):
    base64_image = encode_image(image)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What text do you see in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    
    return response.choices[0].message.content

st.title("照片文字辨識應用")

uploaded_file = st.file_uploader("上傳一張照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='上傳的圖片', use_column_width=True)
    
    if st.button('開始辨識文字'):
        with st.spinner('正在處理中...'):
            result = perform_ocr(uploaded_file)
        st.success('處理完成!')
        st.write("辨識結果:")
        st.write(result)
