import os
import re
from datetime import datetime, timedelta
import tiktoken
from gpt_client import check_title_similarity
from difflib import SequenceMatcher


def remove_brackets(text):
    # "신입" 또는 "채용"이 포함된 경우 대괄호 안의 내용은 유지하고, 나머지 특수기호와 소괄호는 제거
    if "신입" in text or "채용" in text:
        # 대괄호 안의 내용은 유지하고, 다른 특수기호와 소괄호는 제거
        text = re.sub(r'\(.*?\)|\]|[<>_\-*/@#$%^&*(),.?":{}|<>]', '', text).strip()
    else:
        # 대괄호와 소괄호 및 모든 특수기호 제거
        text = re.sub(r'\[.*?\]|\(.*?\)|\]|[<>_\-*/@#$%^&*(),.?":{}|<>]', '', text).strip()

    return text


def truncate_text(text, max_tokens):  # 토큰 수 이하로 자르기
    encoding = tiktoken.get_encoding("cl100k_base")

    # 텍스트를 토큰으로 인코딩
    tokens = encoding.encode(text)

    # 최대 토큰 수로 자르기
    truncated_tokens = tokens[:max_tokens]

    # 토큰을 다시 텍스트로 디코딩
    truncated_text = encoding.decode(truncated_tokens)

    return truncated_text


def calculate_similarity(a, b):
    # 입력된 두 문자열 간의 유사도 계산
    return SequenceMatcher(None, a, b).ratio()


def is_recent_title_duplicate(new_title, filename='titles.txt'):
    recent_titles = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                # 저장된 라인에서 날짜와 시간을 추출하고, 제목만 남김
                saved_datetime, saved_title = line.strip().split('$')
                saved_date = datetime.strptime(saved_datetime, '%Y-%m-%d %H:%M:%S')
                if saved_date > datetime.now() - timedelta(days=7):
                    recent_titles.append((saved_date, saved_title))

    # 최신 제목들을 날짜 기준으로 정렬하고 100개 이하로 자르기
    recent_titles.sort(reverse=True, key=lambda x: x[0])  # 최신순으로 정렬
    recent_titles = [title for _, title in recent_titles[:100]]  # 100개 이하로 자름

    # 각 제목에 대해 특수기호 제거
    cleaned_titles = [remove_brackets(title).strip() for title in recent_titles]

    # 원시적인 텍스트 유사도 검사 (80% 이상이면 중복으로 간주)
    for title in cleaned_titles:
        if calculate_similarity(new_title, title) >= 0.8:
            return '중복'

    # GPT를 사용해 중복 여부 판단
    return check_title_similarity(new_title, cleaned_titles)


def save_title(title, filename='titles.txt'):
    with open(filename, 'a', encoding='utf-8') as file:
        # 날짜와 시간을 함께 저장
        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}${title}\n")
