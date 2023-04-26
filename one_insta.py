import csv
import datetime
import random
import time
import json
from instagrapi import Client
from instagrapi.exceptions import ClientError
import os
import requests

row_count = 1

# vpn 테스트
#  60

# username = "moret64614"
# password = "snstest1"

username = "serij83151"
password = "snstest1"


def login_user():
    cl = Client()
    # cl.set_proxy("http://135.181.82.250:8080")
    print('🌳 계정 리스트 로딩.')
    with open('user-agent.json', 'r') as file:
        user_agents = json.load(file)

    user_agent = random.choice(user_agents)
    try:
        session = cl.load_settings(f"./sessions/{username}.json")
        if session:
            print('세션 정보를 활용해 로그인을 시도합니다.')
            try:
                cl.set_settings(session)
                cl.login(username, password)
                cl.dump_settings(f"./sessions/{username}.json")

                try:
                    cl.get_timeline_feed()
                except:
                    print("세션이 만료되었습니다. 아이디와 비밀번호를 사용해 세션을 갱신합니다.")

                    old_session = cl.get_settings()

                    cl.set_settings({})
                    cl.set_uuids(old_session["uuids"])

                    cl.login(username, password)
                    cl.dump_settings(f"./sessions/{username}.json")
            except Exception as e:
                print("세션 정보를 활용해 로그인에 실패했습니다.: %s" % e)
    except:
        print(f'🥔 {username} 로그인을 시도합니다.')
        cl.set_user_agent(user_agent)
        cl.login(username, password)
        cl.dump_settings(f"./sessions/{username}.json")
        print(f'🥔 {username} 로그인 완료.')

    return cl


def search_posts_by_hashtag(client, hashtag, max_posts=50):
    global row_count
    print(f'🏎️ "{hashtag}" 해시태그에서 {max_posts}개의 개시물을 불러옵니다.')
    posts = client.hashtag_medias_recent(hashtag, amount=max_posts)
    print('✅ 불러오기 완료!')
    row_count += 1
    print(row_count)
    return posts


# def random_user_agent():
#     return random.choice(user_agents)


def download_media(url, local_path):
    response = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(response.content)


def pretreatment_data(posts, hashtag, shop):
    filtered_posts = []

    # 현재 시간(UTC 기준) 가져오기
    current_date_utc = datetime.datetime.now(datetime.timezone.utc).date()

    print(f"'{hashtag}' 해시태그의 최근 게시물 목록:")
    for post in posts:
        post_date = post.taken_at.date()
        days_diff = (current_date_utc - post_date).days
        if days_diff <= 1:  # 오늘 이전으로 부터 1일 이내인지 확인
            print(
                f"- 게시물 ID: {post.id}, 캡션: {post.caption_text}, 업로드 날짜: {post_date}")
            caption_text_words = post.caption_text.split()
            # hashtag와 shop 문자열이 분리된 caption_text_words에 모두 포함되어 있는지 확인
            if all(s in caption_text_words for s in [f"#{hashtag}"]) and any(s in caption_text_words for s in [f"#@{shop}", f"@{shop}"]):
                filtered_posts.append(post)
        else:
            print(
                f"- 게시물 ID: {post.id}, 캡션: {post.caption_text}, 업로드 날짜: {post_date} (1일 이내 게시물 아님)")

    return filtered_posts


def save_posts_to_csv(posts, hashtag, shop, file_name="posts.csv"):
    if not posts:
        return

    filtered_posts = pretreatment_data(hashtag=hashtag, shop=shop, posts=posts)

    if not filtered_posts:
        return

    print('🛵 게시물을 csv에 저장합니다....')
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
            print(post)

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
        print('✅ 저장 완료!')


# 실제 응답 모델 테스팅용
# class Media:
#     def __init__(self, pk: str, id: str, code: str, taken_at: datetime, caption_text: str):
#         self.pk = pk
#         self.id = id
#         self.code = code
#         self.taken_at = taken_at
#         self.caption_text = caption_text


if __name__ == "__main__":
    print('🥔 로그인을 시도합니다.')
    client = login_user()
    print('✅ 로그인 성공!')

    request_count = 0

    # posts = search_posts_by_hashtag(client, "3509a0b1")
    # posts = [Media(pk='3034098679218183034', id='3034098679218183034_57304107125', code='CobSKxkSBt6', taken_at=datetime.datetime(2023, 4, 20, 00, 19, 29, tzinfo=datetime.timezone.utc), caption_text='#조공 #조앤강 😻\n너무너무 귀여워 ... \n@choandkang_official #조공 #오키로스틱화이트 #6a699\n@erounmart_kr #조공 #한방보양삼계탕전 #1e6656ff'),
    #          Media(pk='3034098679218183034', id='3034098679218183034_57304107125', code='CobSKxkSBt6', taken_at=datetime.datetime(2023, 4, 20, 00, 19, 29, tzinfo=datetime.timezone.utc), caption_text='#조공 #조앤강 😻\n너무너무 귀여워 ... \n@choandkang_official #조공 #오키로스틱화이트 #6a699\n@erounmart_kr #조공 #한방보양삼계탕전 #1e6656ff'),
    #          Media(pk='3034098679218183034', id='3034098679218183034_57304107125', code='CobSKxkSBt6', taken_at=datetime.datetime(2023, 4, 23, 00, 19, 29, tzinfo=datetime.timezone.utc), caption_text='#조공 #조앤강 😻\n너무너무 귀여워 ... \n@choandkang_official #조공 \n@liferecipe.official #조공 #한방보양삼계탕전 #1e6656ff'),
    #          Media(pk='3034098679218183034', id='3034098679218183034_57304107125', code='CobSKxkSBt6', taken_at=datetime.datetime(2023, 4, 21, 00, 19, 29, tzinfo=datetime.timezone.utc), caption_text='#조공 #조앤강 😻\n너무너무 귀여워 ... \n@choandkang_official #조공 \n@lowti_official #조공 #한방보양삼계탕전 #1e6656ff')]
    # save_posts_to_csv(posts=posts, hashtag="#6a699", shop='@erounmart_kr', file_name=f"snsreview.csv")

    posts = search_posts_by_hashtag(client, "5265830a")
    save_posts_to_csv(posts=posts, hashtag="5265830a",
                      shop='romistory_com', file_name=f"snsreview.csv")

    # with open("./hashtag_shop.csv", "r", encoding='utf-8') as csvfile:
    #     csv_reader = csv.reader(csvfile)
    #     start_line = 11
    #     row_count = start_line

    #     for line_number, row in enumerate(csv_reader, start=1):
    #         if line_number <= start_line:
    #             continue

    #         hashtag = row[0]
    #         shop = row[1]
    #         print(f'🔎 해시태그 처리 시작: {hashtag}')
    #         try:
    #             if request_count == 30:
    #                 sleep_duration = random.randint(180, 300)
    #                 print(f'⏲️ {sleep_duration}초 동안 대기합니다.')

    #             posts = search_posts_by_hashtag(client, hashtag)
    #             save_posts_to_csv(posts=posts, shop=shop, hashtag=hashtag, file_name=f"snsreview.csv")

    #             request_count += 1
    #             sleep_duration = random.randint(1, 300)
    #             print(f'⏲️ {sleep_duration}초 동안 대기합니다.')
    #             time.sleep(sleep_duration)
    #         except Exception as e:
    #             if request_count == 30:
    #                 sleep_duration = random.randint(180, 300)
    #                 print(f'⏲️ {sleep_duration}초 동안 대기합니다.')

    #             print('🥔 세션 만료 30초 대기 후 로그인을 시도합니다.')
    #             client.logout()

    #             time.sleep(30)

    #             client = login_user()

    #             posts = search_posts_by_hashtag(client, hashtag)
    #             save_posts_to_csv(posts=posts, shop=shop, hashtag=hashtag, file_name=f"snsreview.csv")

    #             request_count += 1
    #             sleep_duration = random.randint(1, 120)
    #             print(f'⏲️ {sleep_duration}초 동안 대기합니다.')
    #             time.sleep(sleep_duration)
