import streamlit as st
import base64
from PIL import Image
import io
from openai import OpenAI
import requests
from datetime import datetime, timedelta
import json
import re

# Initialize session state
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = None
if 'extracted_info' not in st.session_state:
    st.session_state.extracted_info = {}

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Google Apps Script URL
GOOGLE_SCRIPT_URL = st.secrets["google_apps_script_url"]

def preprocess_image(image_file):
    image = Image.open(image_file)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    max_size = (1000, 1000)
    image.thumbnail(max_size, Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def perform_ocr(image):
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts specific information from medical documents."},
                {"role": "user", "content": f"From the following text, please extract the date, time, location, medical department, and doctor's name. Return the information in a JSON format with keys 'date', 'time', 'location', 'department', and 'doctor'. If any information is not available, set the value to null. Here's the text:\n\n{ocr_result}"}
            ],
            max_tokens=200
        )
        content = response.choices[0].message.content
        st.write("GPT-4 Response:", content)  # Debug output
        
        # Try to parse as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract information using regex
            st.write("JSON parsing failed. Attempting regex extraction.")
            info = {}
            patterns = {
                'date': r'date["\s:]+([^,"}\s]+)',
                'time': r'time["\s:]+([^,"}\s]+)',
                'location': r'location["\s:]+([^,"}\s]+)',
                'department': r'department["\s:]+([^,"}\s]+)',
                'doctor': r'doctor["\s:]+([^,"}\s]+)'
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                info[key] = match.group(1) if match else None
            return info
    except Exception as e:
        st.error(f"提取信息時發生錯誤：{str(e)}")
        return {}

def create_calendar_event(title, date, time, location):
    start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end_datetime = start_datetime + timedelta(hours=1)

    event_data = {
        "title": title,
        "location": location,
        "startDateTime": start_datetime.isoformat(),
        "endDateTime": end_datetime.isoformat()
    }

    st.write(f"正在發送請求到 Google Apps Script: {GOOGLE_SCRIPT_URL}")
    st.write(f"事件數據: {json.dumps(event_data, ensure_ascii=False, indent=2)}")

    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=event_data)
        st.write(f"收到響應。狀態碼: {response.status_code}")
        st.write(f"響應內容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return f"事件已成功添加到日曆。事件 ID: {result.get('eventId')}"
            else:
                return f"添加事件時發生錯誤: {result.get('message')}"
        else:
            return f"請求失敗。狀態碼: {response.status_code}, 響應: {response.text}"
    except requests.RequestException as e:
        return f"發送請求時發生錯誤: {str(e)}"
    except json.JSONDecodeError:
        return f"無法解析響應 JSON。響應內容: {response.text}"

st.title("醫療文件文字辨識與日曆預約應用")

st.write("""
這個應用程序可以從上傳的醫療文件圖片中辨識文字，提取關鍵信息，並幫助您預約 Google 日曆。
""")

uploaded_file = st.file_uploader("上傳一張照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='上傳的圖片', use_column_width=True)
    
    if st.button('開始辨識文字並提取信息', key='process_image'):
        with st.spinner('正在處理圖片...'):
            st.session_state.ocr_result = perform_ocr(uploaded_file)
            if "處理圖片時發生錯誤" in st.session_state.ocr_result:
                st.error(st.session_state.ocr_result)
            else:
                st.success('OCR處理完成!')
                st.write("OCR辨識結果:")
                st.write(st.session_state.ocr_result)
                
                with st.spinner('正在提取信息...'):
                    st.session_state.extracted_info = extract_information(st.session_state.ocr_result)
                st.success('信息提取完成!')
                st.write("提取的信息:")
                st.write(st.session_state.extracted_info)

if st.session_state.extracted_info:
    st.write("請檢查並編輯提取的信息：")
    
    st.session_state.extracted_info['date'] = st.text_input("日期", st.session_state.extracted_info.get('date', ''))
    st.session_state.extracted_info['time'] = st.text_input("時間", st.session_state.extracted_info.get('time', ''))
    st.session_state.extracted_info['location'] = st.text_input("地點", st.session_state.extracted_info.get('location', ''))
    st.session_state.extracted_info['department'] = st.text_input("科別", st.session_state.extracted_info.get('department', ''))
    st.session_state.extracted_info['doctor'] = st.text_input("醫生", st.session_state.extracted_info.get('doctor', ''))

    if st.button('預約日曆', key='create_event'):
        st.write("預約日曆按鈕被點擊")
        
        title = f"預約回診-{st.session_state.extracted_info['department']}+{st.session_state.extracted_info['doctor']}"
        date = st.session_state.extracted_info['date']
        time = st.session_state.extracted_info['time']
        location = st.session_state.extracted_info['location']

        st.write(f"提取的信息: 科別={st.session_state.extracted_info['department']}, 醫生={st.session_state.extracted_info['doctor']}, 日期={date}, 時間={time}, 地點={location}")

        if date and time and location:
            result = create_calendar_event(title, date, time, location)
            st.write("日曆事件創建結果:")
            st.write(result)
        else:
            st.error("無法創建日曆事件。請確保日期、時間和地點信息都已填寫。")

st.write("""
注意：
1. 請確保上傳的圖片清晰可讀。
2. 如果某些信息無法從圖片中提取，您可以手動輸入或修正。
3. 點擊"預約日曆"按鈕將會在您的 Google 日曆中創建一個事件。
4. 確保您有權限訪問指定的日曆。
""")
