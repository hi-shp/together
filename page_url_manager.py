import pandas as pd
import numpy as np
from string_function import extract_domain_part


class AnnouncementPage:
    def __init__(self, page_url, default_url) -> None:
        self.page_url = page_url
        self.default_url = default_url
        # self.notice_board_name = notice_board_name


class PageUrlManager:
    def __init__(self):
        filename = "C:\\together-main\\Source\\pages.csv"
        df = pd.read_csv(filename)
        self.announcement_pages = np.array([])
        self.__init_announcement_pages(df)

    def __init_announcement_pages(self, data):
        for page_url in data.iloc[:, 0]:
            self.announcement_pages = np.append(
                self.announcement_pages, AnnouncementPage(
                    page_url=page_url,
                    default_url=extract_domain_part(page_url, "pusan.ac.kr")
                )
            )


if __name__ == '__main__':
    PageUrlManager()
