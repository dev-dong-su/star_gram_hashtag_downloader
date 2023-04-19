import csv
import random
import json
import time
from instagrapi import Client
import os
import logging
import threading
import requests

# row_count = 509
row_count = 1000
hashtag_file = 1
row_count_lock = threading.Lock()

logger = logging.getLogger()


def login_user(account_index):
    cl = Client()

    user_agent = random_user_agent()
    random_device = generate_random_device()
    username = data['account'][account_index]['id']
    password = data['account'][account_index]['password']

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
        cl.set_device(random_device)
        print(cl.settings)
        cl.login(username, password)
        cl.dump_settings(f"./sessions/{username}.json")
        print(f'🥔 {username} 로그인 완료.')

    update_account_status(account_index, "running")
    return cl


def generate_random_device():
    return random.choice(device)


def random_user_agent():
    return random.choice(user_agents)


def search_posts_by_hashtag(client, hashtag, account_index, max_posts=1):
    global row_count
    row_count += 1
    print(row_count)

    print(f'🏎️ {account_index}번 스레드:  "{hashtag}" 해시태그에서 {max_posts}개의 개시물을 불러옵니다.')
    posts = client.hashtag_medias_recent(hashtag, amount=max_posts)
    print('✅ 불러오기 완료!')
    return posts


def download_media(url, local_path):
    response = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(response.content)


def save_posts_to_csv(posts, hashtag, file_name="posts.csv"):
    if not posts:
        return

    print('🛵 게시물을 csv에 저장합니다....')
    image_directory = f'images/{hashtag}'
    video_directory = f'video/{hashtag}'

    if not os.path.exists(image_directory):
        os.makedirs(image_directory)

    with open(file_name, mode="a", newline='', encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        csv_writer.writerow(['permalink', 'media_id', 'username', 'caption_text',
                            'hashtag', 'like_count', 'comment_count', 'local_file_path'])

        for post in posts:
            # 단일 사진 게시물 처리
            if post.media_type == 1:
                tmp_local_directory = os.path.join(
                    image_directory, post.user.username)

                if not os.path.exists(tmp_local_directory):
                    os.makedirs(tmp_local_directory)
                local_file_path = os.path.join(
                    tmp_local_directory, f"{post.pk}.jpg")
                media_urls = post.thumbnail_url
                download_media(media_urls, local_file_path)

            # 영상 게시물 처리
            elif post.media_type == 2:
                tmp_video_directory = os.path.join(
                    video_directory, post.user.username)
                if not os.path.exists(tmp_video_directory):
                    os.makedirs(tmp_video_directory)

                media_urls = post.video_url
                download_media(media_urls, local_video_file_path)

            # 사진, 영상 묶음 게시물 처리
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
                        tmp_local_directory, f"{post.pk}.jpg")
                    download_media(index.thumbnail_url, local_file_path)
                    media_urls.append(local_file_path)

            else:
                media_urls = ''

            csv_writer.writerow([f'https://www.instagram.com/p/{post.code}', post.id,  post.user.username,
                                post.caption_text, hashtag, post.like_count, post.comment_count, local_file_path])
        print('✅ 저장 완료!')


def process_hashtags(client, account_index, account_list):
    global row_count
    global hashtag_file

    request_count = 0
    thread_delay_count = 0
    max_request_count = random.randint(30, 40)

    while True:
        with row_count_lock:
            hashtag = hashtags[row_count - 1]
            row_count += 1

        try:
            if thread_delay_count == random.randint(10, 20):
                time.sleep(120)
                print(
                    f'⏲️ {account_index}번 {sleep_duration}요청 사이에 120초 동안 대기합니다.')

            posts = search_posts_by_hashtag(client, hashtag, account_index)
            save_posts_to_csv(posts, hashtag, f"snsreview.csv")

            sleep_duration = random.randint(10, 20)
            print(f'⏲️ {account_index} 번 {sleep_duration}초 동안 대기합니다.')
            time.sleep(sleep_duration)

            thread_delay_count += 1
            request_count += 1  # 요청 횟수 증가

            # 요청 횟수가 40에 도달하면, 계정을 교체
            if request_count >= max_request_count:
                # 현재 계정 상태를 'ready'로 변경
                update_account_status(account_index, "ready")
                ready_accounts = [i for i, account in enumerate(
                    account_list) if account["status"] == "ready"]  # 'ready'인 계정 목록을 가져옴

                if not ready_accounts:
                    print("모든 계정이 사용 중이거나 차단되었습니다. 대기 후 다시 시도합니다.")
                    time.sleep(180)
                    ready_accounts = [i for i, account in enumerate(
                        account_list) if account["status"] == "ready"]

                account_index = random.choice(
                    ready_accounts)  # 'ready'인 계정 중 하나를 선택
                client = login_user(account_index)  # 새로운 계정으로 로그인합니다.
                request_count = 0  # 요청 횟수를 초기화합니다.
                max_request_count = random.randint(30, 40)

        except Exception as e:
            print(f'🥔 {account_index} 번 인스타에게 들켰습니다! 30초 대기 후 로그인을 시도합니다.')
            time.sleep(30)

            update_account_status(account_index, "ban")

            ready_accounts = [i for i, account in enumerate(
                account_list) if account["status"] == "ready"]  # 'ready'인 계정 목록을 가져옴

            if not ready_accounts:
                print("모든 계정이 사용 중이거나 차단되었습니다. 대기 후 다시 시도합니다.")
                time.sleep(180)
                ready_accounts = [i for i, account in enumerate(
                    account_list) if account["status"] == "ready"]

            account_index = random.choice(
                ready_accounts)  # 'ready'인 계정 중 하나를 선택
            client = login_user(account_index)  # 새로운 계정으로 로그인합니다.
            request_count = 0

            posts = search_posts_by_hashtag(client, hashtag, account_index,)
            save_posts_to_csv(posts, hashtag, f"snsreview.csv")

            sleep_duration = random.randint(10, 20)
            print(f'⏲️ {account_index} 번  {sleep_duration}초 동안 대기합니다.')
            time.sleep(sleep_duration)


def update_account_status(account_index, new_status):
    data['account'][account_index]['status'] = new_status
    with open('account.json', 'w') as file:
        json.dump(data, file)


if __name__ == "__main__":
    print('🌳 필요한 변수를 로딩합니다.')

    print('🌳 계정 리스트 로딩.')
    with open('account.json', 'r') as file:
        data = json.load(file)
    print(f'{len(data)}개 로딩 완료.')

    print('🌳 User Agent 리스트 로딩.')
    with open('user-agent.json', 'r') as file:
        user_agents = json.load(file)

    print('🌳 Device 리스트 로딩.')
    with open('device.json', 'r') as file:
        device = json.load(file)

    print(f'{len(device)}개 로딩 완료.')

    # 해시태그 읽어오기
    with open(f"./hashtags/hashtag목록_{hashtag_file}.csv", "r", encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        hashtags = [row[0] for row in csv_reader]
        num_lines = len(hashtags)

    available_accounts = [
        account for account in data['account'] if account["status"] != "ban"]

    num_accounts = len(available_accounts)

    clients = [login_user(i) for i in range(1) if i < num_accounts]

    threads = [threading.Thread(target=process_hashtags, args=(
        client, i, available_accounts)) for i, client in enumerate(clients)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
