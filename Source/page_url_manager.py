import pandas as pd
from dotenv import load_dotenv
import os


def extract_domain_part(url, domain):
    domain_index = url.find(domain)
    if domain_index == -1:
        return url

    path_start_index = url.find('/', domain_index + len(domain))
    if path_start_index == -1:
        return url
    else:
        return url[:path_start_index]


class AnnouncementPage:
    def __init__(self, department, page_url, default_url, number=0) -> None:
        self.department = department  # 학과명 추가
        self.page_url = page_url
        self.default_url = default_url
        self.number = number  # 공지 번호 추가, 기본값은 0


class PageUrlManager:
    def __init__(self):
        load_dotenv()
        filename = os.getenv("PAGE_NAME")
        df = pd.read_csv(f'{filename}')
        self.announcement_pages = []
        self.__init_announcement_pages(df)

    def __init_announcement_pages(self, data):
        for _, row in data.iterrows():
            department = row['department'] if 'department' in row and pd.notna(row['department']) else ""
            page_url = row['page_url']
            number_str = str(row['number']) if 'number' in row and pd.notna(row['number']) else "0"
            number = int(float(number_str))  # 소수점 포함된 숫자 처리

            self.announcement_pages.append(
                AnnouncementPage(
                    department=department,  # 학과명 추가
                    page_url=page_url,
                    default_url=extract_domain_part(page_url, "pusan.ac.kr"),
                    number=number
                )
            )

        # 리스트를 역순으로 정렬
        # self.announcement_pages.reverse()
