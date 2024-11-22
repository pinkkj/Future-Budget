import re
from sentence_transformers import SentenceTransformer, util
import openai
openai.api_key = "api"
client = openai

# 1차 카테고리 분류 함수
def first_preprocessing(data):
    # 카테고리 정의
    categories = {
        '식비': ['식사', '음식', '레스토랑', '우아한형제들', '맥도날드', '파리바게뜨', '맘스터치', '버거킹', '토스트', '리앤이라마띠네경', '쿠팡이츠'],
        '카페, 간식': ['간식', '커피', '스타벅스', '이디야', '카페', '할리스', '카페 베네', '투썸 플레이스', '엔제리너스', '커핀','그루나루', '탐앤탐스', '투썸', '유멜로우', '칸나'],
        '편의점, 마트': ['마트', '편의점', '장보기', '지에스25', 'gs25','GS25', '씨유', '시유', 'CU', 'cu', '세븐일레븐', '노브랜드', '홈플러스', '이마트'],
        '술, 유흥': [],
        '생활, 쇼핑': ['아트박스', '다이소', '홈플러스', '노브랜드', '쿠팡', '세탁'],
        '패션, 뷰티': ['지그재그', '무신사', '에이블리', '올리브', 'ABLY'],
        '취미, 여가, 운동': ['보드게임', 'PC', '포토'],
        '의료': ['약국', '의원', '병원', '치과', '이비인후과', '내과'],
        '주거, 통신': [],
        '교통, 자동차': ['교통', '택시', '법인'],
        '여행, 숙박': [],
        '교육': [],
        '이체': [],
        '간편 결제': ['토스', '카카', '네이버', 'GSPay', 'GS페', 'Apple', '간편'],
        '기타':[]
    }

    # 분류 함수
    def classify_transaction(description):
        if len(description) == 3:
            return '이체'
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in description:
                    return category
        return 'NULL'

    data['카테고리'] = data['거래내용'].apply(classify_transaction)

    data = data[data['출금액'] != 0]

    # '거래내용'에 "토스" 다음에 세 글자가 오는 경우 "카테고리"를 "이체"로 분류
    data['카테고리'] = data.apply(lambda row: '이체' if re.search(r'토스\s?\w{3}', row['거래내용']) else row['카테고리'], axis=1)

    return data

# 2차 전처리 함수
def second_preprocessing(data):
    categories = {
        "식비": "식사, 음식, 외식, 점심, 저녁, 요리, 식품",
        "카페, 간식": "커피, 음료, 디저트, 간식, 카페",
        "편의점, 마트": "편의점, 마트, 장보기",
        "술, 유흥": "술, 유흥, 바, 클럽, 맥주, 와인, 요리주점",
        "생활, 쇼핑": "생활, 생활용품, 잡화, 쇼핑, 가전, 세탁",
        "패션, 뷰티": "의류, 패션, 뷰티, 화장품, 옷",
        "취미, 여가, 운동": "취미, 여가, 스포츠, 운동, 게임, PC",
        "의료": "병원, 의료, 약국, 진료, 의원",
        "주거, 통신": "주거, 월세, 인터넷, 통신",
        "교통, 자동차": "대중교통, 택시, 자동차, 기차, 버스",
        "여행, 숙박": "여행, 숙박, 호텔, 리조트, 항공, 공항",
        "교육": "교육, 학원, 공부, 강의, 프린트, 오피스, 문구",
        "이체": "계좌 이체, 송금, 금융, 뱅킹",
        "간편 결제": "카카오페이, 토스, 간편 결제, QR 결제",
        "기타": " "
    }

    def get_chatgpt_response(query):
        completion = openai.ChatCompletion.create(
            messages=[{"role": "user", "content": query}],
            model="gpt-3.5-turbo",
        )
        return completion.choices[0].message.content.strip()

    model = SentenceTransformer('jhgan/ko-sroberta-multitask')

    def categorize_response(response, categories, threshold=0.35):
        response_embedding = model.encode(response, convert_to_tensor=True)
        category_embeddings = {cat: model.encode(desc, convert_to_tensor=True) for cat, desc in categories.items()}
        similarities = {cat: util.cos_sim(response_embedding, emb).item() for cat, emb in category_embeddings.items()}
        best_category = max(similarities, key=similarities.get)
        return best_category if similarities[best_category] >= threshold else "기타"

    transaction_category_map = {}

    def categorize_transaction(row):
        transaction_content = row['거래내용']
        if transaction_content in transaction_category_map:
            return transaction_category_map[transaction_content]
        chatgpt_response = get_chatgpt_response(transaction_content)
        predicted_category = categorize_response(chatgpt_response, categories)
        transaction_category_map[transaction_content] = predicted_category
        return predicted_category

    data.loc[data['카테고리'] == 'NULL', '카테고리'] = data.loc[data['카테고리'] == 'NULL'].apply(categorize_transaction, axis=1)
    return data

def apply_category_mapping(data):
    data = first_preprocessing(data)
    data = second_preprocessing(data)
    return data