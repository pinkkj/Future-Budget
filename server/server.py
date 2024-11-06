from flask import Flask, request, jsonify
import pandas as pd
import os
from datetime import datetime
import pytz
import re
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
from googleapiclient.discovery import build
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# YouTube Data API 키
api_key ="AIzaSyDSESYYtUoiqq1wmAmS0pE-53c_le3YIhk"
youtube = build('youtube', 'v3', developerKey=api_key)

# 감정 분석 모델 로드
model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# 클라이언트 IP 주소 가져오기
def get_client_id():
    return request.remote_addr

def clean_youtube_description(description):
    description = re.sub(r"ㅡ{3,}[\s\S]*?ㅡ{3,}", "", description, flags=re.DOTALL)
    hashtags = re.findall(r"#\S+", description)
    keywords = [tag.strip('#') for tag in hashtags] if hashtags else None
    description = re.sub(r"http\S+|www.\S+", "", description)
    description = re.sub(r"#\S+", "", description)
    description = re.sub(r"\n+", "\n", description)
    cleaned_description = description.strip()
    return cleaned_description, keywords

def extract_meaningful_sentences(text, keywords):
    if not keywords:
        return None
    unwanted_phrases = [
        "씨리얼.*?구독하고", "인스타그램", "페이스북", "톡 플러스 친구",
        "다 들어줄 개", "어플", "검색", "구독", "문자와 톡", "문자 보내면", "상담받을 수 있다고"
    ]
    for phrase in unwanted_phrases:
        text = re.sub(phrase, "", text, flags=re.IGNORECASE)
    meaningful_sentences = []
    for sentence in text.split('\n'):
        if any(keyword in sentence for keyword in keywords) and len(sentence) > 0:
            meaningful_sentences.append(sentence.strip())
    meaningful_text = "\n".join(meaningful_sentences).strip()
    return meaningful_text if meaningful_text else None

def classify_emotion(text):
    tokens = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        prediction = model(**tokens)
    prediction = F.softmax(prediction.logits, dim=1)
    output = prediction.argmax(dim=1).item()
    labels = ["매우 부정적", "부정적", "중립", "긍정적", "매우 긍정적"]
    return labels[output]

# 영상 정보 수집 함수
def get_video_info(video_url, client_ip):
    kst = pytz.timezone('Asia/Seoul')
    current_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    video_id = re.search(r"shorts/([^?&]+)", video_url) or re.search(r"v=([^&]+)", video_url)

    if video_id:
        video_id = video_id.group(1)
    else:
        return {"error": "유효하지 않은 유튜브 링크입니다."}
    
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()

    if "items" in response and len(response["items"]) > 0:
        video_info = response["items"][0]
        title = video_info["snippet"]["title"]
        raw_description = video_info["snippet"]["description"]
        description, keywords = clean_youtube_description(raw_description)
        meaningful_description = extract_meaningful_sentences(description, keywords)
        
        texts_to_analyze = [title, meaningful_description, ", ".join(keywords) if keywords else None]
        combined_text = " ".join(filter(lambda x: x and isinstance(x, str), texts_to_analyze))

        if combined_text:
            emotion = classify_emotion(combined_text)
        else:
            emotion = "NULL"

        duration = video_info["contentDetails"]["duration"]

        # 데이터프레임에 클라이언트 IP 주소 추가
        data = {
            "Timestamp": current_time,
            "IP Address": client_ip,
            "Title": title,
            "Description": description,
            "Meaningful Description": meaningful_description if meaningful_description else "NULL",
            "Duration": duration,
            "Keywords": ", ".join(keywords) if keywords else "NULL",
            "Emotion": emotion,
            "End Time": "NULL"
        }
        
        save_to_excel(data)
        return data
    else:
        return {"error": "동영상 정보를 찾을 수 없습니다."}

# CSV 파일에 데이터 저장 함수
def save_to_excel(data):
    file_name = "youtube_data.xlsx"
    df = pd.DataFrame([data])
    
    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        if not ((existing_df['Timestamp'] == data['Timestamp']) & 
                (existing_df['Title'] == data['Title'])).any():
            updated_df = pd.concat([existing_df, df], ignore_index=True)
            updated_df.to_excel(file_name, index=False, engine="openpyxl")
    else:
        df.to_excel(file_name, index=False, engine="openpyxl")

# analyze_video 엔드포인트
@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    video_url = request.json.get('url')
    if not video_url:
        return jsonify({"error": "URL이 제공되지 않았습니다."}), 400

    client_ip = get_client_id()  # 클라이언트 IP 주소 가져오기
    result = get_video_info(video_url, client_ip)  # IP 주소를 get_video_info 함수로 전달

    return jsonify(result)

# end_video 엔드포인트: IP 주소로 'End Time' 업데이트
@app.route('/end_video', methods=['POST'])
def end_video():
    file_name = "youtube_data.xlsx"
    client_ip = get_client_id()
    end_time = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")

    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        
        # pd.isnull()을 사용해 'End Time'이 비어 있는지 확인하고, 최근 것 하나만 선택
        mask = (df['IP Address'] == client_ip) & (pd.isnull(df['End Time']))

        if mask.any():
            last_index = df.loc[mask].index[-1]  # 업데이트할 마지막 인덱스 가져오기
            df.loc[last_index, 'End Time'] = end_time  # 원본 DataFrame에 직접 할당
            df.to_excel(file_name, index=False, engine="openpyxl")
            return jsonify({"message": "최근 항목의 종료 시간이 저장되었습니다.", "End Time": end_time})
        else:
            return jsonify({"error": "업데이트할 'End Time'이 비어 있는 항목이 없습니다."}), 404
    else:
        return jsonify({"error": "CSV 파일이 존재하지 않습니다."}), 404


# 서버 실행
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
