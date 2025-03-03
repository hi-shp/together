from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from typing import List
from crawl_announcement import Announcement
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
import time
import pandas as pd
from selenium.common.exceptions import NoAlertPresentException
import base64
import re

class WriteNoticeService:
    def __init__(self):
        load_dotenv()
        window_size = os.getenv('WINDOW_SIZE')
        user_agent = os.getenv('USER_AGENT')
        chrome_driver_path = os.getenv('CHROME_DRIVER_PATH')

        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('no-sandbox')
        options.add_argument(f'window-size={window_size}')
        options.add_argument('disable-gpu')
        options.add_argument('lang=ko_KR')
        options.add_argument(f'user-agent={user_agent}')

        driver_service = Service(chrome_driver_path)
        self.driver = webdriver.Chrome(service=driver_service, options=options)
        self.driver.get('https://plato.pusan.ac.kr/')

        # 로그인 수행
        self.login(os.getenv('PLATO_ID'), os.getenv('PLATO_PW'))

    def login(self, id: str, pw: str):
        username_input = self.driver.find_element(By.ID, 'input-username')
        username_input.send_keys(id)

        password_input = self.driver.find_element(By.ID, "input-password")
        password_input.send_keys(pw)

        submit = self.driver.find_element(By.NAME, "loginbutton")
        submit.click()

    def move_to_course(self, course_url: str):
        self.driver.get(course_url)

    def move_to_notice_board(self, notice_board_name: str):
        notice_board_link = self.driver.find_element(By.XPATH,
                                                     f'//a[span[contains(@class, "instancename") and contains(text(), "{notice_board_name}")]]')
        notice_board_link.click()

    def download_survey(self):
        self.driver.get("https://plato.pusan.ac.kr/mod/feedback/view.php?id=2007210")
        # 응답 보기 버튼 클릭
        response_view_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "응답 보기"))
        )
        response_view_button.click()
        # 다운로드 버튼 클릭
        download_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "다운로드")]'))
        )
        download_button.click()
        download_path = r"C:\Users\Park\Downloads\알림 신청하기.csv"
        # 파일이 다운로드될 때까지 기다리기 (최대 10초)
        wait_time = 0
        while not os.path.exists(download_path) and wait_time < 10:
            time.sleep(0.1)
            wait_time += 0.1

        if os.path.exists(download_path):
            df = pd.read_csv(download_path, encoding="utf-8-sig")  # CSV 파일 로드

            df_message = df[['이름', '학번', '(선택/복수 가능) 학과', '(선택/복수 가능) 알림 설정']].copy()  # 필요한 컬럼 추출
            df_message['Plato 쪽지 여부'] = df_message['(선택/복수 가능) 알림 설정'].apply(
                lambda x: 'Plato 쪽지' in str(x))  # 'Plato 쪽지' 포함 여부 확인
            df_message.to_csv(r"C:\Users\Park\Downloads\message.csv", index=False, encoding="utf-8-sig")  # 결과 저장

            df_email = df[['이름', '(선택/복수 가능) 학과', '(선택/복수 가능) 알림 설정', '이메일 주소']].copy()  # 필요한 컬럼 추출
            df_email['Email 여부'] = df_email['(선택/복수 가능) 알림 설정'].apply(lambda x: '이메일' in str(x))  # '이메일' 포함 여부 확인
            df_email.to_csv(r"C:\Users\Park\Downloads\email.csv", index=False, encoding="utf-8-sig")  # 결과 저장

    def send_message(self, title, url, department):
        # 쪽지 보내기 버튼 클릭 → 학번/이름 기반 체크박스 클릭 → 쪽지 작성 및 전송
        message_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '쪽지 보내기')]"))
        )
        message_button.click()

        # message.csv 파일 로드
        df_messages = pd.read_csv(r"C:\Users\Park\Downloads\message.csv", dtype={'학번': str}, encoding="utf-8-sig")  # 학번을 문자열(str)로 처리

        if "(선택/복수 가능) 학과" in df_messages.columns:
            df_messages.rename(columns={"(선택/복수 가능) 학과": "department"}, inplace=True)

        # department 열에서 NaN을 빈 문자열("")로 변환 후 줄바꿈(\n) 기준으로 리스트 변환
        df_messages["department"] = df_messages["department"].fillna("").astype(str).apply(lambda x: x.split("\n"))

        # 플라토 쪽지를 선택한 사용자 필터링
        selected_users = df_messages[df_messages["(선택/복수 가능) 알림 설정"].astype(str).str.contains("Plato 쪽지", na=False)]

        # department 리스트에 현재 department가 포함된 사용자 찾기
        filtered_users = selected_users[selected_users["department"].apply(lambda dept_list: department in dept_list)]

        # 학번과 이름 가져오기
        student_ids = filtered_users["학번"].tolist()
        student_names = filtered_users["이름"].tolist()

        if student_ids:
            # 체크박스 클릭 (학생 이름 & 학번 기반)
            for student_id, student_name in zip(student_ids, student_names):
                try:
                    # XPath를 이용해 정확한 이름과 학번을 포함하는 라벨 찾기
                    user_label_xpath = f"//label[contains(text(), '{student_name} ({student_id})')]"

                    # 해당 라벨이 있는지 확인
                    user_label = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, user_label_xpath))
                    )

                    # 라벨과 연결된 체크박스의 ID 가져오기
                    checkbox_id = user_label.get_attribute("for")  # ex: "form-user-442452"

                    # 체크박스 찾기
                    checkbox_xpath = f"//input[@id='{checkbox_id}']"
                    checkbox = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, checkbox_xpath))
                    )

                    # 체크박스 클릭
                    checkbox.click()

                except Exception as e:
                    print(f"{student_name} ({student_id}) 체크 실패: {str(e)}")

            # 메시지 입력 필드 찾기
            message_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@name='message']"))
            )

            # 메시지 내용
            message_text = f"✔ [{department}] 새로운 공지가 등록되었습니다.\n제목: {title}\n{url}"

            # 메시지 입력
            message_input.send_keys(message_text)

            # 쪽지 전송 버튼 클릭
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '쪽지 전송')]"))
            )
            send_button.click()
            try:
                WebDriverWait(self.driver, 5).until(EC.alert_is_present())  # 최대 5초 동안 Alert 대기
                alert = self.driver.switch_to.alert
                alert.accept()  # Alert 닫기 (확인 버튼 클릭)
            except NoAlertPresentException:
                print("Alert 없음")

            print(f"{department}/Plato 쪽지 전송 완료 ({len(student_ids)}명)")
        self.move_to_course("https://plato.pusan.ac.kr/course/view.php?id=157301")

    def send_email(self, title, url, content, department):
        # 이메일 보내기 버튼 클릭 → 이름/이메일 기반 체크박스 클릭 → 메일 작성 및 전송
        email_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '이메일 보내기')]"))
        )
        email_button.click()

        # email.csv 파일 로드
        df_email = pd.read_csv(r"C:\Users\Park\Downloads\email.csv", encoding="utf-8-sig")

        if "(선택/복수 가능) 학과" in df_email.columns:
            df_email.rename(columns={"(선택/복수 가능) 학과": "department"}, inplace=True)

        # department 열에서 NaN을 빈 문자열("")로 변환 후 줄바꿈(\n) 기준으로 리스트 변환
        df_email["department"] = df_email["department"].fillna("").astype(str).apply(lambda x: x.split("\n"))

        # 이메일을 선택한 사용자 필터링
        selected_users = df_email[df_email["(선택/복수 가능) 알림 설정"].astype(str).str.contains("이메일", na=False)]

        # department 리스트에 현재 department가 포함된 사용자 찾기
        filtered_users = selected_users[selected_users["department"].apply(lambda dept_list: department in dept_list)]

        # 이름과 이메일 가져오기
        student_names = filtered_users["이름"].tolist()
        email_addresses = filtered_users["이메일 주소"].tolist()

        if email_addresses:
            # 체크박스 클릭 (학생 이름 & 이메일 기반)
            for student_name, email in zip(student_names, email_addresses):
                try:
                    # XPath를 이용해 정확한 이름과 이메일이 포함된 라벨 찾기
                    user_label_xpath = f"//label[contains(@title, '{student_name} ({email})')]"

                    # 해당 라벨이 있는지 확인
                    user_label = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, user_label_xpath))
                    )

                    # 라벨과 연결된 체크박스의 ID 가져오기
                    checkbox_id = user_label.get_attribute("for")  # 예: "form-user-442452"

                    # 체크박스 찾기
                    checkbox_xpath = f"//input[@id='{checkbox_id}']"
                    checkbox = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, checkbox_xpath))
                    )

                    # 체크박스 클릭
                    checkbox.click()

                except Exception as e:
                    print(f"{student_name} ({email}) 체크 실패: {str(e)}")

            # 제목 입력 필드 찾기
            subject_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "subject"))
            )

            # 제목 입력 (형식: ✔ [department] title)
            subject_text = f"✔ [{department}] {title}"
            subject_input.send_keys(subject_text)

            # 메시지 입력 필드 찾기
            message_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_messageeditable"))
            )

            # HTML 메일 기본 구조
            message_text = f"""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>2025학년도 1학기 [투게더] 부산대학교 모든 공지사항</title>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        <p>[{department}] 새로운 공지가 등록되었습니다.</p>
                        <br>
                        <p><strong>제목: {title}</strong></p>
                        <p><a href="{url}">{url}</a></p>
                        <br>
                    </div>
                </div>
            </body>
            </html>
            """

            # BeautifulSoup을 사용하여 HTML 파싱
            soup = BeautifulSoup(message_text, 'html.parser')

            # 공지사항 URL 태그 찾기
            url_tag = soup.find('a', href=True)

            if url_tag:
                # 받은 content HTML을 BeautifulSoup 객체로 변환
                content_soup = BeautifulSoup(content, 'html.parser')

                # <br> 태그 생성
                br_tag = content_soup.new_tag('br')

                # 먼저 content를 삽입하고, 그 앞에 <br> 태그 추가
                url_tag.insert_after(content_soup)
                url_tag.insert_after(br_tag)

            # 이미지 파일을 Base64로 변환 (이메일에서 표시되도록)
            with open(r"C:\together-main\Source\together.png", "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')

            # Base64 이미지 태그 생성
            image_base64 = f"data:image/png;base64,{encoded_string}"

            # 하단 투게더 정보 추가
            footer = soup.find("div", class_="container")
            if footer:
                # Base64 이미지 추가
                together_image = soup.new_tag("img",
                                              src=image_base64,
                                              alt="TOGETHER 배너",
                                              width="350",
                                              height="51",
                                              style="max-width: 100%; height: auto; user-select: auto !important;",
                                              class_="img-responsive atto_image_button_text-bottom"
                                              )

                # 설명 텍스트 추가 (작은 글씨, 중앙 정렬)
                together_text = soup.new_tag("p",
                                             style="font-size: 12px; color: #777;")
                together_text.string = "부산대학교의 모든 공지사항을 한곳에서 편리하게, 자율강좌 투게더"

                # 링크 추가 (작은 글씨, 중앙 정렬)
                together_link = soup.new_tag("a", href="https://plato.pusan.ac.kr/course/view.php?id=157301",
                                             style="font-size: 12px; color: #007bff; display: block;")
                together_link.string = "https://plato.pusan.ac.kr/course/view.php?id=157301"

                # footer에 요소 추가 (이미지 → 텍스트 → 링크 순서)
                footer.append(together_image)
                footer.append(together_text)
                footer.append(together_link)

            # 최종 HTML 출력
            final_email_content = str(soup)

            # Selenium을 통해 HTML 입력 (입력 이벤트 강제 트리거)
            self.driver.execute_script("""
                arguments[0].innerHTML = arguments[1];
                arguments[0].focus();
                arguments[0].dispatchEvent(new Event('focus', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                arguments[0].blur();
            """, message_input, final_email_content)

            # 이메일 전송 버튼 클릭
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '이메일 전송')]"))
            )
            send_button.click()

            print(f"{department}/이메일 전송 완료 ({len(email_addresses)}명)")
        self.move_to_course("https://plato.pusan.ac.kr/course/view.php?id=157301")

    def write_notices(self, course_url: str, announcements: List[Announcement], department):
        self.move_to_course(course_url)

        for announcement in announcements:
            self.move_to_notice_board(announcement.notice_board_name)
            self.write_notice_in_board(announcement.title, announcement.url, announcement.content_html,
                                       announcement.files, announcement.notice_board_name, department)

            # 공지 작성 후 코스 페이지로 돌아가기
            self.move_to_course(course_url)


    def write_notice_in_board(self, subject: str, url: str, content: str, files: List[str], notice_board_name: str, department: str):

        # department에서 소괄호와 그 안의 내용 제거 후 띄어쓰기 제거
        department_cleaned = re.sub(r"\([^)]*\)", "", department).replace(" ", "")

        if notice_board_name in ["기타 공지사항", "장학금"]:
            subject = f"[{department_cleaned}] {subject}"
        else:
            subject = f"⭐{subject}"

        # '쓰기' 버튼을 찾고 화면에 나타날 때까지 스크롤 (공지글이 많으면 버튼이 밀림)
        write_button = WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//a[contains(@class, "btn btn-primary") and contains(text(), "쓰기")]'))
        )

        # 스크롤하여 요소가 보이도록 함
        self.driver.execute_script("arguments[0].scrollIntoView(true);", write_button)
        write_button.click()

        # 제목 입력
        input_subject = self.driver.find_element(By.NAME, "subject")
        input_subject.send_keys(subject)

        # 본문 입력
        input_content = self.driver.find_element(By.ID, "id_contenteditable")

        # 본문 최상단에 공지사항 링크 추가
        content_with_link = f'<p>본문 링크 : <a href="{url}">{url}</a></p>' + content

        # BeautifulSoup을 사용하여 이미지 태그에 클래스 추가 (화면 맞춤)
        soup = BeautifulSoup(content_with_link, 'html.parser')
        images = soup.find_all('img')
        for img in images:
            img['class'] = img.get('class', []) + ['img-responsive', 'atto_image_button_text-bottom']

        content_with_styles = str(soup)

        # Selenium을 통해 내용을 입력 (입력 이벤트 강제 트리거)
        self.driver.execute_script("""
            arguments[0].innerHTML = arguments[1];
            arguments[0].focus();
            arguments[0].dispatchEvent(new Event('focus', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            arguments[0].blur();
        """, input_content, content_with_styles)

        """
        # "장학금" 게시판이 아닌 경우에만 공지 글로 설정 (체크박스 클릭)
        if notice_board_name != "장학금":
            notice_checkbox = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_notice"))
            )
            if not notice_checkbox.is_selected():
                notice_checkbox.click()
        """

        # 파일 업로드 수행
        if files and notice_board_name != "기타 공지사항":
            self.upload_files(files)  # 파일 업로드 실행

            try:
                # 파일 업로드 입력 필드가 사라질 때까지 대기 (최대 2초)
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
            except:
                print("⚠️ 파일 입력 필드가 사라지지 않았지만 저장 버튼을 클릭합니다.")

            # 업로드 후 저장 버튼 클릭
            self.click_with_js('input[type="submit"].btn-primary')

        else:
            # 파일이 없거나 notice_board_name이 "기타 공지사항"이면 바로 저장
            self.click_with_js('input[type="submit"].btn-primary')

    def upload_files(self, files: List[str]):
        for file_path in files:
            self.upload_file(file_path)

    def upload_file(self, file_path: str):
        # 첨부파일 요소 찾기 및 클릭
        self.click_with_js('a[role="button"][title="추가 ..."].btn.btn-default.btn-sm')

        # 파일 선택 요소 찾기
        file_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
        )

        # 파일 경로를 절대 경로로 변환
        absolute_path = os.path.abspath(file_path)

        # 파일 경로를 입력하여 파일 선택
        file_input.send_keys(absolute_path)

        # 파일 업로드 버튼 클릭
        self.click_with_js('button.fp-upload-btn.btn-primary.btn')

    def click_with_js(self, css_selector: str):
        element = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        self.driver.execute_script("arguments[0].click();", element)

    def remove_stars(self, course_url: str, today_date: str):
        # 체크할 게시판 리스트
        board_names = [
            "교육/특강/프로그램", "[공모전] 공학/IT/SW", "[공모전] 아이디어/기획",
            "[공모전] 미술/디자인/건축", "[공모전] 문학/수기/에세이", "[공모전] 기타",
            "봉사활동", "서포터즈", "취업 정보"
        ]

        for board_name in board_names:
            self.move_to_course(course_url)

            board_link_element = self.driver.find_element(By.XPATH,
                                                          f'//a[span[contains(@class, "instancename") and contains(text(), "{board_name}")]]')
            board_url = board_link_element.get_attribute("href")  # URL 가져오기
            board_link_element.click()

            print(f"\n현재 작업 중인 게시판: {board_name}")

            page = 1  # 첫 페이지부터 시작
            while True:
                current_url = self.update_page_url(board_url, page)
                self.driver.get(current_url)

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                    )

                    rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                    found_star = False

                    # 별이 있는 게시글을 수정하면, 그 게시글을 제외하고 탐색하도록 설정
                    last_checked_index = len(rows) - 1  # 초기값: 마지막 행부터 탐색

                    while last_checked_index > -1:
                        try:
                            row = rows[last_checked_index]

                            try:
                                title_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) a")
                                notice_url = title_element.get_attribute("href")
                                date_selector = "td:nth-child(5)"
                            except Exception:
                                title_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(4) a")
                                notice_url = title_element.get_attribute("href")
                                date_selector = "td:nth-child(6)"

                            title_text = title_element.text.strip()
                            date_element = row.find_element(By.CSS_SELECTOR, date_selector)
                            date_text = date_element.text.strip()

                            if date_text == today_date:
                                last_checked_index -= 1
                                continue

                            if title_text.startswith("⭐"):
                                new_title = title_text[1:].strip()
                                found_star = True  # 별이 있는 경우 found_star를 True로 설정

                                # 공지글 페이지 이동
                                self.driver.get(notice_url)
                                WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'modify')]"))
                                )

                                # 수정 버튼 다시 찾기 (stale element 방지)
                                modify_button = self.driver.find_element(By.XPATH, "//a[contains(@class, 'modify')]")
                                modify_link = modify_button.get_attribute("href")
                                modify_link = modify_link.replace("&amp;", "&")

                                # 수정 페이지로 이동
                                self.driver.get(modify_link)
                                WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.NAME, "subject"))
                                )

                                # 제목 수정
                                self.update_title(new_title)
                                print(f"수정 완료: {new_title}")

                                # 별 제거 후 다시 게시판 페이지로 돌아감
                                self.driver.get(current_url)
                                WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                                )

                                # 기존 방식과 달리, 다시 전체 `rows`를 가져오지 않고 현재 인덱스(`last_checked_index`) 이후의 글만 탐색하도록 설정
                                rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")  # 새롭게 로드된 rows 가져오기
                                last_checked_index -= 1  # 현재 인덱스를 하나 감소하여 다음 글 탐색
                                continue

                        except Exception as e:
                            print(f"오류 발생: {e}")

                        last_checked_index -= 1  # 다음 글로 이동

                    if not found_star:
                        if board_name == "취업 정보":
                            print("모든 게시판 수정 완료")
                        else:
                            print(f"{board_name} 게시판 수정 완료 → 다음 게시판으로 이동")
                        break  # 별이 하나도 없으면 다음 게시판으로 이동

                    page += 1

                except Exception as e:
                    print(f"오류 발생: {e}")
                    break

    def update_page_url(self, base_url: str, page: int) -> str:
        # URL의 page 파라미터를 변경하여 반환
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        query_params["page"] = [str(page)]
        new_query = urlencode(query_params, doseq=True)
        return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"

    def update_title(self, new_title: str):
        # 제목에서 별을 제거하고 저장하는 함수
        input_subject = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "subject"))
        )
        input_subject.clear()
        input_subject.send_keys(new_title)

        # 변경사항 저장
        self.click_with_js('input[type="submit"].btn-primary')

    def update_participants(self):

        # 참여자 목록 페이지로 이동
        self.driver.get("https://plato.pusan.ac.kr/user/users.php?id=157301")

        # HTML 파싱
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # 맨 위 참가자 숫자 가져오기
        first_cell = soup.find('td', class_='cell c1 number text-center column-number')
        if first_cell:
            highest_number = int(first_cell.text.strip())  # 숫자로 변환
        else:
            return  # 숫자를 찾지 못하면 종료

        # 쉼표 추가된 형식으로 변환
        formatted_number = "{:,}".format(highest_number)

        # 편집 페이지로 이동
        self.driver.get("https://plato.pusan.ac.kr/course/editsection.php?id=1814053&sr")

        # 'id_summary_editoreditable' 요소가 로드될 때까지 대기
        content_div = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_summary_editoreditable"))
        )

        # 기존 HTML 가져오기 (Selenium에서 직접 가져옴)
        original_content = content_div.get_attribute("innerHTML")

        # 기존 숫자 찾기 및 업데이트
        if "명이 함께하고 있습니다." in original_content:
            old_text = original_content.split("현재 ")[1].split("명이 함께하고 있습니다.")[0].strip()
            new_content = original_content.replace(old_text, formatted_number)

            # Selenium을 통해 입력 (입력 이벤트 강제 트리거)
            self.driver.execute_script("""
                arguments[0].innerHTML = arguments[1];
                arguments[0].focus();
                arguments[0].dispatchEvent(new Event('focus', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                arguments[0].blur();
            """, content_div, new_content)

            # 저장 버튼 클릭
            save_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "submitbutton"))
            )
            save_button.click()