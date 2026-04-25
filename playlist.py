import argparse
import csv
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# 1. API 클라이언트 설정
scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_authenticated_service():
    # GCP에서 다운로드받은 OAuth 2.0 클라이언트 ID 파일 필요
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "client_secret.json" 

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(port=0)
    
    return googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

# 2. 재생목록 생성 함수
def create_playlist(youtube, title, description=""):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": title,
            "description": description
          },
          "status": {
            "privacyStatus": "private" # 생성 시 기본 비공개
          }
        }
    )
    response = request.execute()
    return response["id"]

# 3. 비디오 검색 함수 (가장 높은 Quota 소모: 100)
def search_video(youtube, query):
    request = youtube.search().list(
        part="id",
        maxResults=1,
        q=query,
        type="video"
    )
    response = request.execute()
    items = response.get("items", [])
    if items:
        return items[0]["id"]["videoId"]
    return None

# 4. 재생목록에 곡 추가 함수 (Quota 소모: 50)
def add_video_to_playlist(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id
            }
          }
        }
    )
    request.execute()

def extract_playlist_id(playlist_input):
    value = playlist_input.strip()
    if not value:
        raise ValueError("재생목록 URL 또는 ID가 비어 있습니다.")

    parsed = urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        return value

    query_values = parse_qs(parsed.query)
    playlist_ids = query_values.get("list")
    if playlist_ids:
        return playlist_ids[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] == "playlist":
        return path_parts[1]

    raise ValueError("URL에서 재생목록 ID를 찾지 못했습니다. 'list='가 포함된 YouTube 재생목록 URL을 넣어주세요.")

def get_playlist_videos(youtube, playlist_id):
    videos = []
    page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if not video_id:
                continue

            title = item.get("snippet", {}).get("title", "")
            videos.append({
                "title": title,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return videos

def save_playlist_urls(videos, output_path):
    path = Path(output_path)
    if path.suffix.lower() == ".csv":
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=["title", "video_id", "url"])
            writer.writeheader()
            writer.writerows(videos)
    else:
        with path.open("w", encoding="utf-8") as file:
            for video in videos:
                file.write(f"{video['url']}\n")

def extract_playlist_urls(youtube, playlist_input, output_path=None):
    playlist_id = extract_playlist_id(playlist_input)
    videos = get_playlist_videos(youtube, playlist_id)

    if output_path:
        save_playlist_urls(videos, output_path)
        print(f"{len(videos)}개 영상 URL 저장 완료: {output_path}")
    else:
        for video in videos:
            print(video["url"])
        print(f"\n총 {len(videos)}개 영상 URL을 가져왔습니다.")

# 실행 제어부
def create_playlists_from_excel(youtube):
    df = pd.read_excel('Categorized_YouTube_Playlist.xlsx', sheet_name='전체 목록 (All Songs)')
    
    # 카테고리별로 그룹화
    grouped = df.groupby('분류 (Category)')
    
    for category, group in grouped:
        print(f"\n[{category}] 재생목록 생성 중...")
        playlist_id = create_playlist(youtube, title=category, description=f"자동 분류된 {category} 재생목록")
        
        for index, row in group.iterrows():
            query = f"{row['아티스트 (Artist)']} {row['곡명 (Title)']}"
            try:
                # 1. 검색 (Quota 주의)
                video_id = search_video(youtube, query)
                if video_id:
                    # 2. 추가
                    add_video_to_playlist(youtube, playlist_id, video_id)
                    print(f"성공: {query}")
                else:
                    print(f"검색 실패: {query}")
                
                # 안전한 API 호출을 위한 딜레이
                time.sleep(1) 
                
            except googleapiclient.errors.HttpError as e:
                print(f"API 에러 발생 (Quota 초과 가능성): {e}")
                return # 에러 발생 시 즉시 중단

def parse_args():
    parser = argparse.ArgumentParser(description="YouTube 재생목록 생성 및 URL 추출 도구")
    parser.add_argument(
        "--extract-urls",
        metavar="PLAYLIST_URL_OR_ID",
        help="YouTube 재생목록 URL 또는 ID에서 영상 URL 목록을 가져옵니다."
    )
    parser.add_argument(
        "--output",
        help="추출한 URL 저장 경로입니다. .csv면 제목/영상ID/URL을 저장하고, 그 외에는 URL만 저장합니다."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    youtube = get_authenticated_service()

    if args.extract_urls:
        extract_playlist_urls(youtube, args.extract_urls, args.output)
        return

    create_playlists_from_excel(youtube)

if __name__ == "__main__":
    main()
