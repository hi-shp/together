import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openai
from typing import List
import tiktoken

# 클래스 정의
class Announcement:
    def __init__(self, title: str, content: str, notice_board_name: str, url: str):
        self.title = title
        self.url = url
        self.content = content
        self.notice_board_name = notice_board_name

class WriteNoticeService:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument("no-sandbox")
        options.add_argument('window-size=2560x1600')
        options.add_argument("disable-gpu")
        options.add_argument("lang=ko_KR")
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36')

        # 명시적으로 경로 설정
        chrome_driver_path = "C:\\together-main\\Source\\chromedriver-win64\\chromedriver.exe"
        self.driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
        self.driver.get('https://plato.pusan.ac.kr/')

    def write_notices(self, id: str, pw: str, course_name: str, announcements: List[Announcement]):
        self.login(id, pw)
        self.move_to_course(course_name)
        for announcement in announcements:
            if announcement.notice_board_name != "해당없음":
                self.move_to_notice_board(announcement.notice_board_name)
                self.write_notice_in_board(announcement.title, announcement.content)

    def login(self, id: str, pw: str):
        username_input = self.driver.find_element(By.ID, 'input-username')
        username_input.send_keys(id)

        password_input = self.driver.find_element(By.ID, "input-password")
        password_input.send_keys(pw)

        submit = self.driver.find_element(By.NAME, "loginbutton")
        submit.click()

    def move_to_course(self, course_name: str):
        course_link = self.driver.find_element(By.XPATH, f'//h3[text()="{course_name}"]/ancestor::a')
        course_link.click()

    def move_to_notice_board(self, notice_board_name: str):
        try:
            notice_board_link = self.driver.find_element(By.XPATH, '//a[contains(span[@class="instancename"], "' + notice_board_name + '")]')
            notice_board_link.click()
        except Exception as e:
            print(f"게시판을 찾을 수 없습니다: {notice_board_name}, 오류: {str(e)}")

    def write_notice_in_board(self, subject: str, content: str):
        write_button = self.driver.find_element(By.XPATH, '//a[contains(text(), "쓰기")]')
        write_button.click()

        input_subject = self.driver.find_element(By.NAME, "subject")
        input_subject.send_keys(subject)

        input_content = self.driver.find_element(By.ID, "id_contenteditable")
        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", input_content, content)
        input_content.click()

        submit_button = self.driver.find_element(By.NAME, "submitbutton")
        submit_button.click()

# 함수 정의
def truncate_text(text, max_tokens):
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)

def get_existing_titles(filename='titles.txt'):
    existing_titles = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                saved_date, saved_title = line.strip().split('|')
                saved_date = datetime.strptime(saved_date, '%Y-%m-%d')
                if saved_date > datetime.now() - timedelta(days=7):
                    existing_titles.append(saved_title)
    return existing_titles

def check_title_similarity(new_title, existing_titles):
    prompt = (
        "다음 제목이 기존 제목들 중 어떠한 하나라도 중복되는지 판단해. 중복이라면 '중복' 아니라면 '중복되지 않음'이라고 말해.\n\n"
        "새로운 제목: {}\n\n"
        "기존 제목들:\n{}\n\n"
        "중복 여부 여부:".format(new_title, "\n".join(existing_titles))
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "절대로 다른 말은 하지마. '중복' 혹은 '중복되지 않음'만 말하는거야"},
            {"role": "user", "content": prompt}
        ]
    )

    return response['choices'][0]['message']['content'].strip()

def save_title(title, filename='titles.txt'):
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(f"{datetime.now().strftime('%Y-%m-%d')}|{title}\n")

def get_recent_anns_from_rss(rss_url: str):
    response = requests.get(rss_url)
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.find_all('item')[:10]
    urls = [item.find('link').get_text() for item in items]
    return urls[::-1]  # 최신순에서 가장 오래된 순으로 변경

def crawl_ann(url: str) -> Announcement:
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(e)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    title_element = soup.find("h2", class_="artclViewTitle")
    title = title_element.get_text(strip=True) if title_element else "Title not found"
    main_section = soup.find('div', class_="artclView")
    content = str(main_section)

    return Announcement(
        title=title,
        url=url,
        notice_board_name="",
        content=content
    )

def answer_gpt(user_content):
    openai.api_key = os.environ.get('GPT_API_KEY')

    messages = [
        {"role": "system", "content": (
            "다음 글을 적절한 카테고리로 분류해서 그 카테고리만 말해.\n\n"
            "[공모전] 공학/IT/SW\n"
            "[공모전] 아이디어/기획\n"
            "[공모전] 미술/디자인/건축\n"
            "[공모전] 사진/영상/UCC\n"
            "[공모전] 문학/수기/에세이\n"
            "[공모전] 기타\n"
            "교육/특강/프로그램\n"
            "장학금\n"
            "서포터즈\n"
            "봉사활동\n"
            "취업 정보\n"
            "그 외 해당되지 않는다면 '해당없음'으로 응답. \n\n"
            "다른 추가적인 내용은 붙이지 말고 분류한 카테고리 혹은 '해당없음'으로만 출력해. 카테고리 명은 절대 바꾸지 말고 그대로 출력해.\n"
            "웬만하면 해당없음으로 하고, 정말 중요해보이는 것만 게시판에 할당하자. 대회나 공모전이 글에 들어가면 무조건 넣고. 장학금, 서포터즈, 봉사활동, 취업이 들어가도 무조건 넣어"
        )},
        {"role": "user", "content": user_content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5 turbo",
        messages=messages
    )

    assistant_content = response['choices'][0]['message']['content'].strip()

    return assistant_content

# 메인 함수
def main():
    load_dotenv()
    id = os.environ.get("PLATO_ID")
    pw = os.environ.get("PLATO_PW")
    course_name = "[테스트]"
    rss_url = "https://koredu.pusan.ac.kr/bbs/koredu/5262/rssList.do?row=50"

    recent_urls = get_recent_anns_from_rss(rss_url)
    existing_titles = get_existing_titles()
    print(existing_titles)

    for url in reversed(recent_urls):  # 최신 글을 먼저 처리하기 위해 리스트를 역순으로
        ann = crawl_ann(url)
        if ann:
            if check_title_similarity(ann.title, existing_titles) == '중복':
                print(f"중복된 제목: {ann.title}")
                continue

            truncated_content = truncate_text(ann.content, 15000)  # 토큰 수 제한
            category = answer_gpt(truncated_content)
            print(f"챗GPT 응답: {category} - {ann.title}")  # 카테고리 출력
            if category in [
                "[공모전] 공학/IT/SW",
                "[공모전] 아이디어/기획",
                "[공모전] 미술/디자인/건축",
                "[공모전] 사진/영상/UCC",
                "[공모전] 문학/수기/에세이",
                "[공모전] 기타",
                "교육/특강/프로그램",
                "장학금",
                "서포터즈",
                "봉사활동",
                "취업 정보"
            ]:
                ann.notice_board_name = category  # 게시판 이름을 업데이트
                WriteNoticeService().write_notices(id, pw, course_name, [ann])
                save_title(ann.title)
                print(f"게시글 작성 완료\n")
            else:
                print(f"해당 카테고리 없음\n")  # 카테고리 없음

if __name__ == "__main__":
    main()
