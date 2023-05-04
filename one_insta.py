import csv
import datetime
import random
import subprocess
import time
import logging
import json
from instagrapi import Client
from requests.exceptions import ProxyError
from urllib3.exceptions import HTTPError
from instagrapi.exceptions import (
    ClientConnectionError,
    ClientForbiddenError,
    ClientLoginRequired,
    ClientThrottledError,
    GenericRequestError,
    PleaseWaitFewMinutes,
    RateLimitError,
    SentryBlock,
)
import os
import requests

row_count = 1

username = "lofem10275"
password = "snstest1"


def login_user():
    cl = Client()
    # cl.set_proxy("http://135.181.82.250:8080")
    # logging.info('🌳 계정 리스트 로딩.')
    # with open('user-agent.json', 'r') as file:
    #     user_agents = json.load(file)

    # user_agent = random.choice(user_agents)

    try:
        session = cl.load_settings(f"./sessions/{username}.json")
        if session:
            logging.info('세션 정보를 활용해 로그인을 시도합니다.')
            try:
                cl.set_settings(session)
                cl.login(username, password)
                cl.dump_settings(f"./sessions/{username}.json")

                try:
                    cl.get_timeline_feed()
                except:
                    logging.info("세션이 만료되었습니다. 아이디와 비밀번호를 사용해 세션을 갱신합니다.")

                    old_session = cl.get_settings()

                    cl.set_settings({})
                    cl.set_uuids(old_session["uuids"])

                    cl.login(username, password)
                    cl.dump_settings(f"./sessions/{username}.json")
            except Exception as e:
                logging.info("세션 정보를 활용해 로그인에 실패했습니다.: %s" % e)
    except:
        logging.info(f'🥔 {username} 로그인을 시도합니다.')
        # cl.set_user_agent(user_agent)
        cl.login(username, password)
        cl.dump_settings(f"./sessions/{username}.json")
        logging.info(f'🥔 {username} 로그인 완료.')

    return cl


def search_posts_by_hashtag(client, hashtag, max_posts=50):
    global row_count
    logging.info(f'🏎️ "{hashtag}" 해시태그에서 {max_posts}개의 개시물을 불러옵니다.')
    posts = client.hashtag_medias_recent(hashtag, amount=max_posts)
    logging.info('✅ 불러오기 완료!')
    row_count += 1
    logging.info(row_count)
    return posts


def download_media(url, local_path):
    response = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(response.content)


def pretreatment_data(posts, hashtag, shop):
    filtered_posts = []

    # 현재 시간(UTC 기준) 가져오기
    current_date_utc = datetime.datetime.now(datetime.timezone.utc).date()

    logging.info(f"'{hashtag}' 해시태그의 최근 게시물 목록:")
    for post in posts:
        post_date = post.taken_at.date()
        days_diff = (current_date_utc - post_date).days
        if days_diff <= 3:  # 오늘 이전으로 부터 1일 이내인지 확인
            logging.info(
                f"- 게시물 ID: {post.id}, 캡션: {post.caption_text}, 업로드 날짜: {post_date}")
            caption_text_words = post.caption_text.split()
            # hashtag와 shop 문자열이 분리된 caption_text_words에 모두 포함되어 있는지 확인
            if all(s in caption_text_words for s in [f"#{hashtag}"]) and any(s in caption_text_words for s in [f"#@{shop}", f"@{shop}"]):
                filtered_posts.append(post)
        else:
            logging.info(
                f"- 게시물 ID: {post.id}, 캡션: {post.caption_text}, 업로드 날짜: {post_date} (1일 이내 게시물 아님)")

    return filtered_posts


def save_posts_to_csv(posts, hashtag, shop, file_name="posts.csv"):
    if not posts:
        return

    filtered_posts = pretreatment_data(hashtag=hashtag, shop=shop, posts=posts)

    if not filtered_posts:
        return

    logging.info('🛵 게시물을 csv에 저장합니다....')
    image_directory = f'images/{hashtag}'
    video_directory = f'video/{hashtag}'

    if not os.path.exists(image_directory):
        os.makedirs(image_directory)

    if not os.path.exists(video_directory):
        os.makedirs(video_directory)

    with open(file_name, mode="a", newline='', encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for post in filtered_posts:
            logging.info(post)

            if post.media_type == 1:
                tmp_local_directory = os.path.join(
                    image_directory, post.user.username)

                if not os.path.exists(tmp_local_directory):
                    os.makedirs(tmp_local_directory)
                local_file_path = os.path.join(
                    tmp_local_directory, f"{post.pk}.jpg")
                media_urls = post.thumbnail_url
                download_media(media_urls, local_file_path)

            elif post.media_type == 2:
                tmp_video_directory = os.path.join(
                    video_directory, post.user.username)
                if not os.path.exists(tmp_video_directory):
                    os.makedirs(tmp_video_directory)

                media_urls = post.video_url
                download_media(media_urls, local_video_file_path)

            elif post.media_type == 8:
                tmp_local_directory = os.path.join(
                    image_directory, post.user.username)

                if not os.path.exists(tmp_local_directory):
                    os.makedirs(tmp_local_directory)

                media_urls = []

                for index in post.resources:
                    if index.media_type == 2:
                        tmp_video_directory = os.path.join(
                            video_directory, post.user.username)
                        if not os.path.exists(tmp_video_directory):
                            os.makedirs(tmp_video_directory)

                        local_video_file_path = os.path.join(
                            tmp_video_directory, f"{post.pk}.mp4")
                        download_media(index.video_url, local_video_file_path)
                        media_urls.append(local_video_file_path)
                        continue

                    local_file_path = os.path.join(
                        tmp_local_directory, f"{index.pk}.jpg")
                    download_media(index.thumbnail_url, local_file_path)
                    media_urls.append(local_file_path)

            else:
                media_urls = ''

            formatted_date = post.taken_at.strftime("%Y-%m-%d %H:%M")
            csv_writer.writerow([f'https://www.instagram.com/p/{post.code}', post.id,  post.user.username,
                                post.caption_text, formatted_date, hashtag, post.like_count, post.comment_count, local_file_path])
        logging.info('✅ 저장 완료!')


def run_command(command):
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)

    return result.returncode


def command_resualt(returncode):
    if returncode == 0:
        returncode = run_command("nordvpn connect")
        if returncode == 0:
            logging.info('vpn 재연결 성공')
            sleep_duration = random.randint(100, 300)
            logging.info(f'⏲️ {sleep_duration}초 동안 대기합니다.')
        else:
            logging.error("VPN 연결에 실패했습니다.")
            return False
    else:
        logging.error("VPN 연결에 실패했습니다.")
        return False


if __name__ == "__main__":
    logging.basicConfig(filename='output.log', filemode='a', level=logging.INFO,
                        format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # returncode = run_command("nordvpn connect")

    logging.info('🥔 로그인을 시도합니다.')
    client = login_user()
    logging.info('✅ 로그인 성공!')

    request_count = 0

    posts = search_posts_by_hashtag(client, "ae21767b")
    save_posts_to_csv(posts=posts, hashtag="ae21767b",
                      shop='romistory_com', file_name=f"snsreview.csv")

    # with open("./hashtag_shop.csv", "r", encoding='utf-8') as csvfile:
    #     csv_reader = csv.reader(csvfile)
    #     start_line = 19
    #     row_count = start_line

    #     for line_number, row in enumerate(csv_reader, start=1):
    #         if line_number <= start_line:
    #             continue

    #         hashtag = row[0]
    #         shop = row[1]
    #         logging.info(f'🔎 해시태그 처리 시작: {hashtag}')
    #         try:
    #             if request_count == 30:
    #                 sleep_duration = random.randint(180, 300)
    #                 logging.info(f'⏲️ {sleep_duration}초 동안 대기합니다.')

    #             posts = search_posts_by_hashtag(client, hashtag)
    #             save_posts_to_csv(posts=posts, shop=shop,
    #                               hashtag=hashtag, file_name=f"snsreview.csv")

    #             request_count += 1
    #             sleep_duration = random.randint(100, 300)
    #             logging.info(f'⏲️ {sleep_duration}초 동안 대기합니다.')
    #             time.sleep(sleep_duration)

    # logging.info(f'🔎 해시태그 처리 완료 파일 명: ./hashtag_shop.csv"')
    # returncode = run_command("nordvpn disconnect")
