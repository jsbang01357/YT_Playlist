import os
from pathlib import Path

import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRET_FILE = Path("client_secret.json")
TOKEN_FILE = Path("token.json")
OAUTH_CALLBACK_PORT = 8080
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_CALLBACK_PORT}/"


def has_client_secret():
    return CLIENT_SECRET_FILE.exists()


def has_saved_token():
    return TOKEN_FILE.exists()


def get_client_secret_status():
    if not CLIENT_SECRET_FILE.exists():
        return {
            "ok": False,
            "type": None,
            "message": "client_secret.json 파일이 없습니다."
        }

    import json

    data = json.loads(CLIENT_SECRET_FILE.read_text(encoding="utf-8"))
    if "installed" in data:
        return {
            "ok": True,
            "type": "Desktop app",
            "message": "Desktop app OAuth 클라이언트입니다."
        }

    if "web" in data:
        redirect_uris = data["web"].get("redirect_uris", [])
        if OAUTH_REDIRECT_URI in redirect_uris:
            return {
                "ok": True,
                "type": "Web application",
                "message": f"Web OAuth 클라이언트에 {OAUTH_REDIRECT_URI}가 등록되어 있습니다."
            }

        return {
            "ok": False,
            "type": "Web application",
            "message": f"Web OAuth 클라이언트에는 승인된 리디렉션 URI로 {OAUTH_REDIRECT_URI}를 등록해야 합니다."
        }

    return {
        "ok": False,
        "type": "Unknown",
        "message": "client_secret.json 형식이 Google OAuth 클라이언트 파일과 다릅니다."
    }


def reset_saved_token():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def get_authenticated_service():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError("client_secret.json 파일을 프로젝트 루트에 넣어주세요.")

        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            SCOPES
        )
        credentials = flow.run_local_server(port=OAUTH_CALLBACK_PORT)
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


def list_my_playlists(youtube):
    playlists = []
    page_token = None

    while True:
        response = youtube.playlists().list(
            part="snippet,contentDetails,status",
            mine=True,
            maxResults=50,
            pageToken=page_token
        ).execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            playlists.append({
                "id": item.get("id", ""),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "privacy_status": item.get("status", {}).get("privacyStatus", ""),
                "item_count": item.get("contentDetails", {}).get("itemCount", 0),
                "published_at": snippet.get("publishedAt", "")
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return playlists


def get_playlist_videos(youtube, playlist_id):
    videos = []
    page_token = None

    while True:
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token
        ).execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("contentDetails", {}).get("videoId")
            if not video_id:
                continue

            videos.append({
                "title": snippet.get("title", ""),
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "playlist_item_id": item.get("id", ""),
                "published_at": snippet.get("publishedAt", "")
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return videos


def create_playlist(youtube, title, description="", privacy_status="private"):
    response = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
    ).execute()
    return response["id"]


def add_video_to_playlist(youtube, playlist_id, video_id):
    response = youtube.playlistItems().insert(
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
    ).execute()
    return response.get("id", "")
