import streamlit as st
import base64
from PIL import Image
import io
from openai import OpenAI

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def preprocess_image(image_file):
    # Open the image
    image = Image.open(image_file)
    
    # Convert to RGB if it's not
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if the image is too large
    max_size = (1000, 1000)  # Maximum width and height
    image.thumbnail(max_size, Image.LANCZOS)
    
    # Save as JPEG
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    
    return buffer

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def perform_ocr(image):
    # Preprocess the image
    processed_image = preprocess_image(image)
    base64_image = encode_image(processed_image)
    
    try:
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
    except Exception as e:
        return f"處理圖片時發生錯誤：{str(e)}"

def extract_information(ocr_result):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 或其他適合的模型
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts specific information from medical documents."},
                {"role": "user", "content": f"From the following text, please extract the date, time, location, medical department, and doctor's name. If any information is not available, state 'Not Found'. Here's the text:\n\n{ocr_result}"}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"提取信息時發生錯誤：{str(e)}"

st.title("醫療文件文字辨識與信息提取應用")

st.write("""
這個應用程序可以從上傳的醫療文件圖片中辨識文字，並提取以下信息：
- 日期
- 時間
- 地點
- 科別
- 醫師姓名

請上傳一張清晰的醫療文件照片，然後點擊"開始辨識文字並提取信息"按鈕。
""")

uploaded_file = st.file_uploader("上傳一張照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='上傳的圖片', use_column_width=True)
    
    if st.button('開始辨識文字並提取信息'):
        with st.spinner('正在處理圖片...'):
            ocr_result = perform_ocr(uploaded_file)
            if "處理圖片時發生錯誤" in ocr_result:
                st.error(ocr_result)
            else:
                st.success('OCR處理完成!')
                st.write("OCR辨識結果:")
                st.write(ocr_result)
                
                with st.spinner('正在提取信息...'):
                    extracted_info = extract_information(ocr_result)
                st.success('信息提取完成!')
                st.write("提取的信息:")
                st.write(extracted_info)

        st.write("如果提取的信息不準確，您可以手動編輯修正：")
        edited_info = st.text_area("編輯提取的信息", extracted_info)
        if st.button('保存編輯後的信息'):
            st.success('信息已更新!')
            st.write("最終信息:")
            st.write(edited_info)

st.write("""
注意：
1. 請確保上傳的圖片清晰可讀。
2. 如果某些信息無法從圖片中提取，將顯示為"Not Found"。
3. 您可以手動編輯和修正提取的信息。
""")
