"""Parse sharing URLs locally. Only reconstructed Google viewer URLs leave the API."""
import re
from urllib.parse import parse_qsl, urlsplit

ID = r"[A-Za-z0-9_-]{1,256}"
FILE = re.compile(rf"/file/(?:u/[0-9]+/)?d/({ID})(?:/(?:view|preview|edit))?/?")
FOLDER = re.compile(rf"/drive/(?:u/[0-9]+/)?folders/({ID})/?")
EDITOR = re.compile(rf"/(document|spreadsheets|presentation)/(?:u/[0-9]+/)?d/({ID})(?:/(?:edit|view|preview))?/?")
INVALID = "Enter a direct HTTPS Google Drive file or folder sharing link."


def parse_drive_link(value):
    if (not isinstance(value, str) or len(value) > 2048 or not value.isascii()
            or any(ord(c) <= 32 or ord(c) == 127 or c == "\\" for c in value)):
        raise ValueError(INVALID)
    try:
        parts = urlsplit(value)
        pairs = parse_qsl(parts.query, strict_parsing=True, keep_blank_values=True)
    except ValueError:
        raise ValueError(INVALID) from None
    host = parts.netloc.lower()
    if parts.scheme != "https" or host not in {"drive.google.com", "docs.google.com"}:
        raise ValueError(INVALID)
    params = dict(pairs)
    allowed = {"usp", "resourcekey", "pli", "ouid", "rtpof", "sd", "gid", "tab"}
    if parts.path == "/open" and host == "drive.google.com":
        allowed.add("id")
    if (len(pairs) != len(params) or params.keys() - allowed
            or any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", v) for v in params.values())):
        raise ValueError(INVALID)
    if parts.fragment and not re.fullmatch(r"(?:gid|heading|slide|bookmark|tab)=[A-Za-z0-9_.-]+", parts.fragment):
        raise ValueError(INVALID)
    if host == "drive.google.com" and (match := FILE.fullmatch(parts.path)):
        kind, key = "file", match[1]
        path = f"/file/d/{key}/view"
    elif host == "drive.google.com" and (match := FOLDER.fullmatch(parts.path)):
        kind, key = "folder", match[1]
        path = f"/drive/folders/{key}"
    elif host == "docs.google.com" and (match := EDITOR.fullmatch(parts.path)):
        kind, key = "file", match[2]
        path = f"/{match[1]}/d/{key}/edit"
    elif host == "drive.google.com" and parts.path == "/open" and re.fullmatch(ID, params.get("id", "")):
        kind, key = "item", params["id"]
        path = f"/open?id={key}"
    else:
        raise ValueError(INVALID)
    if "resourcekey" in params:
        path += ("&" if "?" in path else "?") + "resourcekey=" + params["resourcekey"]
    return f"https://{host}{path}", kind, key
