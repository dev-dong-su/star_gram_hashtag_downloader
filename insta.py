import csv
import random
import time
from instagrapi import Client
import os
import logging
from dotenv import load_dotenv
import requests


logger = logging.getLogger()

print('🌳 환경변수를 로딩합니다.')
load_dotenv()

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

def login_user():
    cl = Client()
    session = cl.load_settings("session.json")

    login_via_session = False
    login_via_pw = False

    if session:
        print('세션 정보를 활용해 로그인을 시도합니다.')
        try:
            cl.set_settings(session)
            cl.login(username, password)

            try:
                cl.get_timeline_feed()
            except:
                print("세션이 올바르지 않습니다. 정확한 아이디와 비밀번호로 로그인 해주세요.")

                old_session = cl.get_settings()

                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])

                cl.login(username, password)
            login_via_session = True
        except Exception as e:
            print("세션 정보를 활용해 로그인에 실패했습니다.: %s" % e)

    if not login_via_session:
        print('세션 정보가 존재하지 않습니다. 환경 변수에 존재하는 아이디와 비밀번호로 로그인에 시도합니다.')
        try:
            print("아이디와 비밀번호를 사용해 로그인에 시도합니다. : %s" % username)
            if cl.login(username, password):
                login_via_pw = True
        except Exception as e:
            print("아이디와 비밀번호로 로그인에 실패했습니다. : %s" % e)

    if not login_via_pw and not login_via_session:
        raise Exception("비밀번호와 세션으로의 로그인 둘다 실패했습니다.")
    
    return cl


def search_posts_by_hashtag(client, hashtag, max_posts=10):
    print(f'🏎️ "{hashtag}" 해시태그에서 {max_posts}개의 개시물을 불러옵니다.')
    posts = client.hashtag_medias_recent(hashtag, amount=max_posts)
    print('✅ 불러오기 완료!')
    return posts


def download_media(url, local_path):
    response = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(response.content)

def save_posts_to_csv(posts, hashtag, file_name="posts.csv"):
    print('🛵 게시물을 csv에 저장합니다....')
    image_directory = f'images/{hashtag}'
    video_directory = f'video/{hashtag}'
    
    if not os.path.exists(image_directory):
        os.makedirs(image_directory)
    
    with open(file_name, mode="a", newline='', encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        csv_writer.writerow(['permalink', 'media_id', 'username', 'caption_text', 'like_count', 'comment_count', 'local_file_path'])

        for post in posts:
            tmp_local_directory = os.path.join(image_directory, post.user.username)
            tmp_video_directory = os.path.join(video_directory, post.user.username)
                
            if not os.path.exists(tmp_local_directory):
                os.makedirs(tmp_local_directory)
                
            if not os.path.exists(tmp_video_directory):
                os.makedirs(tmp_video_directory)
                
            local_file_path = os.path.join(tmp_local_directory, f"{post.pk}.jpg")
            local_video_file_path = os.path.join(tmp_video_directory, f"{post.pk}.mp4")
            
            if post.media_type == 1:
                media_urls = post.thumbnail_url
                download_media(media_urls, local_file_path)
                
            elif post.media_type == 2:
                media_urls = post.video_url
                download_media(media_urls, local_video_file_path) 
                
                
            elif post.media_type == 8:
                media_urls = []
                
                for index in post.resources:
                    if index.media_type == 2:
                        download_media(index.video_url, local_video_file_path) 
                        media_urls.append(local_video_file_path)
                        continue
                        
                    download_media(index.thumbnail_url, local_file_path)
                    media_urls.append(local_file_path)
                
            else:
                media_urls = ''
                
            csv_writer.writerow([f'https://www.instagram.com/p/{post.code}', post.id,  post.user.username, post.caption_text, post.like_count, post.comment_count, local_file_path])
        print('✅ 저장 완료!')

if __name__ == "__main__":
    print('🥔 로그인을 시도합니다.')
    client = login_user()
    print('✅ 로그인 성공!')
    
    # hashtag = '웃긴영상레전드'
    # posts = search_posts_by_hashtag(client, hashtag)
    # save_posts_to_csv(posts, hashtag, f"snsreview.csv")
    
    with open("hashtag.csv", "r") as csvfile:
        csv_reader = csv.reader(csvfile)

        for row in csv_reader:
            hashtag = row[0]
            print(f'🔎 해시태그 처리 시작: {hashtag}')

            posts = search_posts_by_hashtag(client, hashtag)
            save_posts_to_csv(posts, hashtag, f"snsreview.csv")

            sleep_duration = random.randint(1, 4)
            print(f'⏲️ {sleep_duration}초 동안 대기합니다.')
            time.sleep(sleep_duration)