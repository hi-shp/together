import requests
from bs4 import BeautifulSoup
import csv


class NoticeUpdater:
    def __init__(self, yesterday_file="yesterday.txt", csv_file="pages.csv"):
        self.yesterday_file = yesterday_file
        self.csv_file = csv_file
        self.urls = [
            "https://www.pusan.ac.kr/kor/CMS/Board/PopupBoard.do?robot=Y&mgr_seq=3&mode=list&page=1",
            "https://www.pusan.ac.kr/kor/CMS/Board/PopupBoard.do?robot=Y&mgr_seq=3&mode=list&page=2"
        ]

    def get_last_notice_title(self):
        """어제의 마지막 공지 제목을 읽어옴"""
        with open(self.yesterday_file, "r", encoding="utf-8") as f:
            return f.readline().strip()

    def fetch_notice_number(self, last_title):
        """공지 제목을 검색하여 동일한 제목의 공지 번호를 찾음"""
        for url in self.urls:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 공지사항 목록에서 제목과 번호 추출
            rows = soup.find_all("tr")

            for row in rows:
                num_tag = row.find("td", class_="num")  # 공지 번호
                title_tag = row.find("td", class_="subject")  # 제목이 포함된 td 태그

                if num_tag and title_tag:
                    title_link = title_tag.find("a")  # 제목이 있는 <a> 태그 찾기
                    if title_link:
                        title = title_link.get_text(strip=True)

                        page_num_text = num_tag.get_text(strip=True).strip()  # 공백 제거 후 숫자 추출

                        if page_num_text.isdigit():  # 숫자인지 확인 후 변환
                            page_num = int(page_num_text)

                            if title == last_title:  # 제목이 일치하면 번호 저장
                                return str(page_num)  # 문자열로 변환하여 반환

        return None  # 찾지 못하면 None 반환

    def update_csv(self, new_number):
        """CSV 파일의 첫 두 줄을 새로운 번호로 업데이트"""
        with open(self.csv_file, "r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            data = list(reader)  # 모든 행을 리스트로 저장

        header = data[0]
        rows = data[1:]

        # 첫 두 개의 대학 공지 데이터만 업데이트, 나머지는 그대로 둠
        updated_rows = []
        for i, row in enumerate(rows):
            department, page_url, number = row
            if i < 2:  # 첫 두 줄만 수정
                updated_rows.append([department, page_url, new_number if new_number else number])
            else:  # 나머지는 그대로 유지
                updated_rows.append(row)

        # 업데이트된 데이터 다시 저장
        with open(self.csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)  # 헤더 작성
            writer.writerows(updated_rows)  # 수정된 데이터 저장
            csvfile.flush()  # 버퍼를 강제로 비움
            csvfile.close()  # 파일을 확실히 닫음

    def fetch_highest_notice_title(self):
        """공지사항 페이지에서 가장 높은 번호(최신 공지)의 전체 제목을 가져옴"""
        response = requests.get(self.urls[0])  # 최신 공지를 검색할 페이지 (page=1)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        highest_number = -1  # 가장 큰 번호를 저장할 변수
        highest_title = None  # 해당 번호의 전체 제목을 저장할 변수
        highest_url = None  # 상세 페이지 URL 저장

        # 모든 공지사항 행 가져오기
        rows = soup.find_all("tr")

        for row in rows:
            num_tag = row.find("td", class_="num")  # 공지 번호
            title_tag = row.find("td", class_="subject")  # 제목이 포함된 td 태그

            if num_tag and title_tag:
                title_link = title_tag.find("a")  # 제목이 있는 <a> 태그 찾기
                if title_link:
                    try:
                        notice_number = int(num_tag.get_text(strip=True))  # 공지 번호를 정수로 변환
                        if notice_number > highest_number:  # 현재까지 가장 높은 번호인지 확인
                            highest_number = notice_number

                            # title 속성이 있으면 가져오고, 없으면 일반 텍스트 가져오기
                            highest_title = title_link.get("title") if title_link.get("title") else title_link.get_text(
                                strip=True)

                            # 만약 제목이 `...`으로 끝나면 개별 페이지에서 가져오기
                            if highest_title.endswith("..."):
                                highest_url = title_link["href"]

                    except ValueError:
                        continue  # 공지 번호가 숫자가 아니면 무시하고 계속 진행

        # 개별 공지 페이지에서 전체 제목 가져오기
        if highest_url:
            highest_title = self.fetch_full_notice_title(highest_url)

        return highest_title

    def fetch_full_notice_title(self, relative_url):
        """개별 공지 페이지에서 전체 제목을 가져옴"""
        base_url = "https://www.pusan.ac.kr/kor/CMS/Board/PopupBoard.do"
        full_url = base_url + relative_url  # 절대 URL 만들기

        response = requests.get(full_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 공지 상세 페이지에서 제목 가져오기 (h4.vtitle 태그 확인)
        title_tag = soup.find("h4", class_="vtitle")
        if title_tag:
            return title_tag.get_text(strip=True)

        return None  # 전체 제목을 찾지 못하면 None 반환

    def update_university_notices(self):
        """가장 높은 번호의 제목을 yesterday.txt의 첫 줄에 저장하고, 기존 공지 업데이트"""
        last_title = self.get_last_notice_title()
        new_number = self.fetch_notice_number(last_title)
        self.update_csv(new_number)
        highest_title = self.fetch_highest_notice_title()

        if highest_title:
            # 기존 데이터 유지하면서 첫 줄만 변경
            with open(self.yesterday_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            lines[0] = highest_title + "\n"  # 첫 줄만 수정

            with open(self.yesterday_file, "w", encoding="utf-8") as f:
                f.writelines(lines)  # 수정된 내용 다시 저장