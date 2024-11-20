import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from flask import render_template

# 과거 월별 소비량
def monthly_consumption(client, font, year_month):
    
    # 설치된 한글 폰트 경로 설정 (예: 맑은 고딕)
    font_path = font  # Windows
    # Linux의 경우: '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

    fontprop = fm.FontProperties(fname=font_path)
    plt.rc('font', family=fontprop.get_name())

    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False
    client_id = client
    file_path = f"./uploads/{client_id}_bank.xlsx"

    if not os.path.exists(file_path):
        return "No data file available."

    df = pd.read_excel(file_path, engine="openpyxl")
    df['거래일시'] = pd.to_datetime(df['거래일시'], errors='coerce')
    df = df.dropna(subset=['거래일시'])

    # year_month를 기반으로 데이터 필터링
    year, month = map(int, year_month.split('-'))
    filtered_df = df[(df['거래일시'].dt.year == year) & (df['거래일시'].dt.month == month)]

    if filtered_df.empty:
        return f"No data for {year_month}"

    # 카테고리별 지출 시각화
    filtered_df['출금액'] = pd.to_numeric(filtered_df['출금액'], errors='coerce').fillna(0)
    monthly_expense = filtered_df.groupby('카테고리')['출금액'].sum()

    # 시각화
    colors = ['#FFB6C1', '#FFDAB9', '#E6E6FA', '#B0E0E6', '#ADD8E6', '#98FB98',
              '#FFE4B5', '#FFD700', '#FFC0CB', '#DDA0DD', '#AFEEEE', '#D3D3D3']

    if not monthly_expense.empty:
        top_3 = monthly_expense.nlargest(3)
        others = monthly_expense.sum() - top_3.sum()
        category_expense = pd.concat([top_3, pd.Series({'기타': others})])

        # 이미지 저장 경로
        img_filename = f"{client_id}_{year_month}_chart.png"
        img_path = os.path.join('static', img_filename)  # 실제 파일 저장 경로

        # 파이차트 생성
        plt.figure(figsize=(8, 8))
        plt.pie(
            category_expense,
            labels=category_expense.index,
            autopct='%1.1f%%',
            startangle=140,
            colors=colors[:len(category_expense)]
        )
        plt.title(f"{year_month} 카테고리별 지출 비율")
        plt.tight_layout()
        plt.savefig(img_path)  # 이미지 저장
        plt.close()
        img_url = f"/static/{img_filename}"
        return render_template('monthly_expenditure.html', img_path=img_url)
    else:
        return f"No expenditure data for {year_month}"

# 모든 월 추세
def monthly_trend(client_id,font):
    # 설치된 한글 폰트 경로 설정 (예: 맑은 고딕)
    font_path = font  # Windows
    # Linux의 경우: '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

    fontprop = fm.FontProperties(fname=font_path)
    plt.rc('font', family=fontprop.get_name())

    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False
    file_path = f"./uploads/{client_id}_bank.xlsx"
    df = pd.read_excel(file_path, engine="openpyxl")
    df['거래일시'] = pd.to_datetime(df['거래일시'], errors='coerce')
    df = df.dropna(subset=['거래일시'])
    df['출금액'] = pd.to_numeric(df['출금액'], errors='coerce').fillna(0)
    df['year_month'] = df['거래일시'].dt.to_period('M')

    # 월별 총 출금액 계산
    monthly_expense = df.groupby('year_month')['출금액'].sum()

    # 선 그래프 생성 및 저장
    img_filename = f"{client_id}_all_months_trend_chart.png"
    img_path = os.path.join('static', img_filename)

    plt.figure(figsize=(12, 6))
    plt.plot(monthly_expense.index.astype(str), monthly_expense.values, marker='o', linestyle='-', color='b')
    plt.title("월별 소비량 변화")
    plt.xlabel("월")
    plt.ylabel("출금액 (KRW)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()

    img_url = f"/static/{img_filename}"
    return img_url

