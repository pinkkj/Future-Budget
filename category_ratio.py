import pandas as pd
import numpy as np
from category_mapping import apply_category_mapping

# 카테고리별 비율
def prepare_data(data):
    data = apply_category_mapping(data)
 
    category_counts = data['카테고리'].value_counts(normalize=True) * 100
    original_ratios = category_counts.to_dict()

    exclude_categories = ["간편 결제", "이체", "기타"]
    filtered_ratios = {k: v for k, v in original_ratios.items() if k not in exclude_categories}
    categories = list(filtered_ratios.keys())
    weights = [1.0] * len(categories)

    df = pd.DataFrame({'카테고리': categories, '원래 비율': list(filtered_ratios.values()), '가중치': weights})
    return df, original_ratios, exclude_categories

# '간편 결제', '이체', '기타'를 제외한 카테고리별 비율
def redistribute_excluded_categories(df, original_ratios, exclude_categories):
    excluded_total_ratio = sum(original_ratios.get(cat, 0) for cat in exclude_categories)
    top_3_indices = df.nlargest(3, '원래 비율').index
    df.loc[top_3_indices, '원래 비율'] += excluded_total_ratio / 3
    return df

# 가장 높은 비율의 카테고리
def get_top_category(data):
    df, original_ratios, exclude_categories = prepare_data(data)
    df = redistribute_excluded_categories(df, original_ratios, exclude_categories)
    top_category = df.loc[df['원래 비율'].idxmax(), '카테고리']
    return top_category

