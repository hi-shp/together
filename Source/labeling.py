import streamlit as st
import pandas as pd

# CSV 파일 경로 설정
FILE_PATH = r"C:\together-main\Source\sorted_labeled_data.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(FILE_PATH, encoding="utf-8-sig", quotechar='"')
    return df

# 데이터 로드 (Session State에서 관리하여 반영 문제 해결)
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# 미분류 데이터 필터링
unlabeled_df = df[df["카테고리"] == "미분류"].copy()

# 카테고리 리스트
categories = [
    "교육/특강/프로그램", "[공모전] 공학/IT/SW", "[공모전] 아이디어/기획",
    "[공모전] 미술/디자인/건축", "[공모전] 문학/수기/에세이", "[공모전] 기타",
    "장학금", "봉사활동", "서포터즈", "취업 정보", "해당없음"
]

# 진행 상태 유지 (현재 라벨링한 개수 저장)
if "index" not in st.session_state:
    st.session_state.index = 0

# 현재 제목 표시
if st.session_state.index < len(unlabeled_df):
    title = unlabeled_df.iloc[st.session_state.index]["제목"]
    st.subheader(f"({st.session_state.index+1}/{len(unlabeled_df)}) {title}")

    # 3열로 나누기
    col1, col2, col3 = st.columns(3)

    selected_category = None

    with col1:
        if st.button(categories[0]):
            selected_category = categories[0]
        if st.button(categories[1]):
            selected_category = categories[1]
        if st.button(categories[2]):
            selected_category = categories[2]
        if st.button(categories[3]):
            selected_category = categories[3]

    with col2:
        if st.button(categories[4]):
            selected_category = categories[4]
        if st.button(categories[5]):
            selected_category = categories[5]
        if st.button(categories[6]):
            selected_category = categories[6]
        if st.button(categories[7]):
            selected_category = categories[7]

    with col3:
        if st.button(categories[8]):
            selected_category = categories[8]
        if st.button(categories[9]):
            selected_category = categories[9]
        if st.button(categories[10]):
            selected_category = categories[10]

    # 선택한 카테고리를 데이터에 반영하고 저장
    if selected_category:
        df.loc[df["제목"] == title, "카테고리"] = selected_category

        # session_state에 df 저장 (이전 데이터 초기화 방지)
        st.session_state.df = df

        #  즉시 CSV 저장
        df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig", quotechar='"')

        # 다음 제목으로 이동
        st.session_state.index += 1

        # 새로고침 없이 데이터 반영
        st.rerun()

