import csv
import io
from urllib.parse import parse_qs, urlparse


VIDEO_ID_COLUMNS = ("video_id", "videoId", "id", "영상ID", "영상 ID")
URL_COLUMNS = ("url", "video_url", "videoUrl", "URL", "영상URL", "영상 URL")
TITLE_COLUMNS = ("title", "제목", "영상 제목", "곡명", "name")


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


def extract_video_id(video_input):
    value = video_input.strip()
    if not value:
        raise ValueError("영상 URL 또는 ID가 비어 있습니다.")

    parsed = urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        return value

    if parsed.netloc.endswith("youtu.be"):
        video_id = parsed.path.strip("/")
        if video_id:
            return video_id

    query_values = parse_qs(parsed.query)
    video_ids = query_values.get("v")
    if video_ids:
        return video_ids[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
        return path_parts[1]

    raise ValueError("URL에서 영상 ID를 찾지 못했습니다.")


def parse_video_inputs(raw_text, remove_duplicates=True):
    videos = []
    seen = set()

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        value = line.strip()
        if not value:
            continue

        try:
            video_id = extract_video_id(value)
        except ValueError as exc:
            videos.append({
                "source": value,
                "line": line_number,
                "video_id": "",
                "url": "",
                "status": f"오류: {exc}"
            })
            continue

        if remove_duplicates and video_id in seen:
            videos.append({
                "source": value,
                "line": line_number,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "status": "중복 제외"
            })
            continue

        seen.add(video_id)
        videos.append({
            "source": value,
            "line": line_number,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "status": "대기"
        })

    return videos


def pick_first_value(row, columns):
    for column in columns:
        value = row.get(column)
        if value:
            return str(value).strip()
    return ""


def parse_video_csv(file_bytes, remove_duplicates=True):
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV 헤더를 찾지 못했습니다.")

    videos = []
    seen = set()

    for row_number, row in enumerate(reader, start=2):
        title = pick_first_value(row, TITLE_COLUMNS)
        video_source = pick_first_value(row, VIDEO_ID_COLUMNS)
        url_source = pick_first_value(row, URL_COLUMNS)
        source = video_source or url_source

        if not source:
            videos.append({
                "title": title,
                "source": "",
                "line": row_number,
                "video_id": "",
                "url": "",
                "status": "오류: video_id 또는 url 컬럼이 필요합니다."
            })
            continue

        try:
            video_id = extract_video_id(source)
        except ValueError as exc:
            videos.append({
                "title": title,
                "source": source,
                "line": row_number,
                "video_id": "",
                "url": "",
                "status": f"오류: {exc}"
            })
            continue

        if remove_duplicates and video_id in seen:
            videos.append({
                "title": title,
                "source": source,
                "line": row_number,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "status": "중복 제외"
            })
            continue

        seen.add(video_id)
        videos.append({
            "title": title,
            "source": source,
            "line": row_number,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "status": "대기"
        })

    return videos


def videos_to_txt(videos):
    return "\n".join(video["url"] for video in videos if video.get("url"))


def videos_to_csv(videos):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["title", "video_id", "url"])
    writer.writeheader()
    for video in videos:
        writer.writerow({
            "title": video.get("title", ""),
            "video_id": video.get("video_id", ""),
            "url": video.get("url", "")
        })
    return output.getvalue().encode("utf-8-sig")
