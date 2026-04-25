import pandas as pd
import streamlit as st
from googleapiclient.errors import HttpError

import playlist_tools
import quota_tracker
import storage
import youtube_client


st.set_page_config(
    page_title="YouTube Playlist Manager",
    page_icon="▶",
    layout="wide"
)


def get_youtube():
    if "youtube" not in st.session_state:
        st.session_state.youtube = youtube_client.get_authenticated_service()
    return st.session_state.youtube


def get_playlists(refresh=False):
    if refresh or "playlists" not in st.session_state:
        youtube = get_youtube()
        playlists = youtube_client.list_my_playlists(youtube)
        st.session_state.playlists = playlists
        storage.save_playlist_cache(playlists)
    return st.session_state.playlists


def playlist_options(playlists):
    return {f"{item['title']} ({item['item_count']})": item for item in playlists}


def require_playlists():
    cache = storage.load_playlist_cache()
    playlists = st.session_state.get("playlists") or cache.get("playlists", [])
    if playlists:
        st.session_state.playlists = playlists
    return playlists


def render_sidebar():
    st.sidebar.header("Connection")
    client_status = youtube_client.get_client_secret_status()
    st.sidebar.write(f"client_secret.json: {'있음' if youtube_client.has_client_secret() else '없음'}")
    st.sidebar.caption(client_status["message"])
    st.sidebar.write(f"token.json: {'있음' if youtube_client.has_saved_token() else '없음'}")

    if st.sidebar.button("YouTube 연결", use_container_width=True):
        try:
            st.session_state.youtube = youtube_client.get_authenticated_service()
            st.sidebar.success("연결 완료")
        except Exception as exc:
            st.sidebar.error(str(exc))

    if st.sidebar.button("토큰 초기화", use_container_width=True):
        youtube_client.reset_saved_token()
        st.session_state.pop("youtube", None)
        st.sidebar.success("token.json을 삭제했습니다.")

    st.sidebar.divider()
    quota_usage = quota_tracker.get_day_usage()
    st.sidebar.header("Quota")
    st.sidebar.metric("오늘 추정 사용량", f"{quota_usage['used']:,} / {quota_usage['limit']:,}")
    st.sidebar.progress(min(quota_usage["usage_ratio"], 1.0))
    st.sidebar.caption(f"남은 추정 quota: {quota_usage['remaining']:,} units")
    if quota_usage["used"] >= quota_usage["limit"]:
        st.sidebar.error("오늘 기본 quota를 모두 쓴 것으로 기록되어 있습니다.")
    elif quota_usage["used"] >= quota_usage["limit"] * 0.8:
        st.sidebar.warning("오늘 quota 사용량이 80%를 넘었습니다.")


def render_playlist_list():
    st.subheader("내 재생목록")
    refresh = st.button("새로고침", type="primary")

    try:
        playlists = get_playlists(refresh=refresh)
    except Exception as exc:
        st.error(str(exc))
        playlists = require_playlists()
        if not playlists:
            return

    if not playlists:
        st.info("재생목록이 없습니다.")
        return

    st.dataframe(
        pd.DataFrame(playlists),
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": "ID",
            "title": "제목",
            "description": "설명",
            "privacy_status": "공개 범위",
            "item_count": "영상 수",
            "published_at": "생성일"
        }
    )


def render_playlist_detail():
    st.subheader("재생목록 상세")
    playlists = require_playlists()
    if not playlists:
        st.info("먼저 내 재생목록을 새로고침하세요.")
        return

    options = playlist_options(playlists)
    selected_label = st.selectbox("재생목록 선택", options.keys())
    selected = options[selected_label]

    if st.button("영상 목록 가져오기", type="primary"):
        try:
            videos = youtube_client.get_playlist_videos(get_youtube(), selected["id"])
            st.session_state.selected_videos = videos
            st.session_state.selected_playlist = selected
            storage.save_playlist_videos(selected["id"], selected["title"], videos)
        except Exception as exc:
            st.error(str(exc))

    videos = st.session_state.get("selected_videos", [])
    if not videos:
        return

    st.caption(f"{len(videos)}개 영상")
    st.dataframe(pd.DataFrame(videos), hide_index=True, use_container_width=True)

    txt_data = playlist_tools.videos_to_txt(videos)
    csv_data = playlist_tools.videos_to_csv(videos)

    left, right = st.columns(2)
    left.download_button(
        "TXT 다운로드",
        data=txt_data,
        file_name=f"{selected['id']}_urls.txt",
        mime="text/plain",
        use_container_width=True
    )
    right.download_button(
        "CSV 다운로드",
        data=csv_data,
        file_name=f"{selected['id']}_videos.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_create_playlist():
    st.subheader("새 재생목록 만들기")
    title = st.text_input("제목")
    description = st.text_area("설명", height=120)
    privacy_status = st.selectbox("공개 범위", ["private", "unlisted", "public"])
    st.caption("예상 quota: 50 units")

    if st.button("재생목록 생성", type="primary"):
        if not title.strip():
            st.warning("제목을 입력하세요.")
            return

        try:
            playlist_id = youtube_client.create_playlist(
                get_youtube(),
                title.strip(),
                description.strip(),
                privacy_status
            )
            st.success(f"생성 완료: {playlist_id}")
            st.session_state.pop("playlists", None)
        except Exception as exc:
            st.error(str(exc))


def render_add_videos():
    st.subheader("영상 URL 일괄 추가")
    playlists = require_playlists()
    if not playlists:
        st.info("먼저 내 재생목록을 새로고침하세요.")
        return

    options = playlist_options(playlists)
    selected_label = st.selectbox("대상 재생목록", options.keys())
    selected = options[selected_label]
    raw_urls = st.text_area("영상 URL 또는 ID를 한 줄에 하나씩 입력", height=180)
    remove_duplicates = st.checkbox("중복 영상 제외", value=True)

    parsed = playlist_tools.parse_video_inputs(raw_urls, remove_duplicates=remove_duplicates)
    if parsed:
        st.dataframe(pd.DataFrame(parsed), hide_index=True, use_container_width=True)
        valid_count = len([item for item in parsed if item["status"] == "대기" and item["video_id"]])
        st.caption(f"예상 quota: {quota_tracker.estimate_video_add(valid_count):,} units")

    if st.button("추가 실행", type="primary"):
        valid_items = [item for item in parsed if item["status"] == "대기" and item["video_id"]]
        if not valid_items:
            st.warning("추가할 수 있는 영상이 없습니다.")
            return

        results = []
        progress = st.progress(0)
        for index, item in enumerate(valid_items, start=1):
            try:
                playlist_item_id = youtube_client.add_video_to_playlist(
                    get_youtube(),
                    selected["id"],
                    item["video_id"]
                )
                results.append({**item, "status": "성공", "playlist_item_id": playlist_item_id})
            except HttpError as exc:
                results.append({**item, "status": f"API 오류: {exc.resp.status}"})
            except Exception as exc:
                results.append({**item, "status": f"오류: {exc}"})
            progress.progress(index / len(valid_items))

        st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
        st.success("추가 작업이 끝났습니다.")


def render_create_from_csv():
    st.subheader("CSV로 재생목록 만들기")
    title = st.text_input("새 재생목록 제목", key="csv_playlist_title")
    description = st.text_area("설명", height=100, key="csv_playlist_description")
    privacy_status = st.selectbox("공개 범위", ["private", "unlisted", "public"], key="csv_privacy_status")
    remove_duplicates = st.checkbox("CSV 안의 중복 영상 제외", value=True, key="csv_remove_duplicates")
    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

    parsed = []
    if uploaded_file:
        try:
            parsed = playlist_tools.parse_video_csv(uploaded_file.getvalue(), remove_duplicates=remove_duplicates)
            st.dataframe(pd.DataFrame(parsed), hide_index=True, use_container_width=True)
            valid_count = len([item for item in parsed if item["status"] == "대기" and item["video_id"]])
            st.caption(f"예상 quota: {quota_tracker.estimate_playlist_create(valid_count):,} units")
        except Exception as exc:
            st.error(str(exc))
            return

    if st.button("CSV로 재생목록 생성", type="primary"):
        if not title.strip():
            st.warning("새 재생목록 제목을 입력하세요.")
            return
        if not uploaded_file:
            st.warning("CSV 파일을 업로드하세요.")
            return

        valid_items = [item for item in parsed if item["status"] == "대기" and item["video_id"]]
        if not valid_items:
            st.warning("추가할 수 있는 영상이 없습니다.")
            return

        try:
            youtube = get_youtube()
            playlist_id = youtube_client.create_playlist(
                youtube,
                title.strip(),
                description.strip(),
                privacy_status
            )
        except Exception as exc:
            st.error(f"재생목록 생성 실패: {exc}")
            return

        results = []
        progress = st.progress(0)
        for index, item in enumerate(valid_items, start=1):
            try:
                playlist_item_id = youtube_client.add_video_to_playlist(
                    get_youtube(),
                    playlist_id,
                    item["video_id"]
                )
                results.append({**item, "status": "성공", "playlist_item_id": playlist_item_id})
            except HttpError as exc:
                results.append({**item, "status": f"API 오류: {exc.resp.status}", "playlist_item_id": ""})
            except Exception as exc:
                results.append({**item, "status": f"오류: {exc}", "playlist_item_id": ""})
            progress.progress(index / len(valid_items))

        storage.save_playlist_videos(playlist_id, title.strip(), results)
        st.session_state.pop("playlists", None)
        st.success(f"재생목록 생성 완료: {playlist_id}")
        st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)


def render_url_extractor():
    st.subheader("URL 추출")
    playlist_input = st.text_input("YouTube 재생목록 URL 또는 ID")

    if st.button("URL 가져오기", type="primary"):
        if not playlist_input.strip():
            st.warning("재생목록 URL 또는 ID를 입력하세요.")
            return

        try:
            playlist_id = playlist_tools.extract_playlist_id(playlist_input)
            videos = youtube_client.get_playlist_videos(get_youtube(), playlist_id)
            st.session_state.extracted_videos = videos
            storage.save_playlist_videos(playlist_id, playlist_id, videos)
        except Exception as exc:
            st.error(str(exc))

    videos = st.session_state.get("extracted_videos", [])
    if not videos:
        return

    st.dataframe(pd.DataFrame(videos), hide_index=True, use_container_width=True)
    st.download_button(
        "URL TXT 다운로드",
        data=playlist_tools.videos_to_txt(videos),
        file_name="playlist_urls.txt",
        mime="text/plain",
        use_container_width=True
    )
    st.download_button(
        "영상 CSV 다운로드",
        data=playlist_tools.videos_to_csv(videos),
        file_name="playlist_videos.csv",
        mime="text/csv",
        use_container_width=True
    )


def render_settings():
    st.subheader("설정")
    client_status = youtube_client.get_client_secret_status()
    st.write(f"OAuth 클라이언트 타입: {client_status['type'] or '없음'}")
    st.write(client_status["message"])
    st.code(youtube_client.OAUTH_REDIRECT_URI)

    cache = storage.load_playlist_cache()
    st.write(f"마지막 재생목록 캐시: {cache.get('last_synced_at') or '없음'}")
    st.write(f"캐시된 재생목록 수: {len(cache.get('playlists', []))}")


def main():
    render_sidebar()

    st.title("YouTube Playlist Manager")

    tabs = st.tabs([
        "내 재생목록",
        "재생목록 상세",
        "새로 만들기",
        "영상 추가",
        "CSV로 만들기",
        "URL 추출",
        "설정"
    ])

    with tabs[0]:
        render_playlist_list()
    with tabs[1]:
        render_playlist_detail()
    with tabs[2]:
        render_create_playlist()
    with tabs[3]:
        render_add_videos()
    with tabs[4]:
        render_create_from_csv()
    with tabs[5]:
        render_url_extractor()
    with tabs[6]:
        render_settings()


if __name__ == "__main__":
    main()
