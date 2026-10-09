"""Small, streaming download primitives with atomic writes and integrity checks."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tempfile
import time
from typing import BinaryIO, Callable
from urllib.parse import urlparse

import requests

FIGSHARE_API = "https://api.figshare.com/v2/articles/7267433"
SOCIOPATTERNS_URL = "https://sociopatterns.org/assets/data/HighSchool2013_proximity_net.csv.gz"
TIMEOUT = (10, 30)
CHUNK_SIZE = 1024 * 1024


class DownloadError(RuntimeError):
    """Acquisition failed; callers may offer retry or manual upload."""


def safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("文件名必须是单个本地文件名，不能包含目录。")
    if "\x00" in name:
        raise ValueError("文件名包含无效字符。")
    return name


@dataclass(frozen=True)
class RemoteFile:
    name: str
    download_url: str
    size: int | None = None
    md5: str | None = None

    def __post_init__(self):
        safe_name(self.name)
        url = urlparse(self.download_url)
        if url.scheme != "https" or not url.netloc:
            raise ValueError("下载地址必须使用 HTTPS。")
        if self.size is not None and (type(self.size) is not int or self.size < 0):
            raise ValueError("元数据文件大小无效。")
        if self.md5 is not None and not re.fullmatch(r"[a-fA-F0-9]{32}", self.md5):
            raise ValueError("元数据 MD5 无效。")


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    skipped: bool
    size: int


def fetch_copenhagen_files(*, session=None, attempts: int = 3) -> list[RemoteFile]:
    """Read names, URLs, sizes and checksums from the live article, never guessed IDs."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    client = session or requests.Session()
    try:
        for attempt in range(attempts):
            try:
                with client.get(FIGSHARE_API, timeout=TIMEOUT) as response:
                    response.raise_for_status()
                    metadata = response.json()
                entries = metadata["files"]
                if not isinstance(entries, list) or not entries:
                    raise ValueError("官方 API 未返回文件清单。")
                files = [
                    RemoteFile(
                        name=item["name"], download_url=item["download_url"],
                        size=item.get("size"), md5=item.get("computed_md5") or item.get("supplied_md5") or None,
                    )
                    for item in entries
                ]
                if len({item.name for item in files}) != len(files):
                    raise ValueError("官方 API 返回重复文件名。")
                return files
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                if attempt + 1 == attempts:
                    raise DownloadError(f"无法读取 Figshare 元数据：{exc}。请重试或从官方页面手动下载。") from exc
                time.sleep(0.2 * (attempt + 1))
    finally:
        if session is None:
            client.close()


def sociopatterns_file() -> RemoteFile:
    return RemoteFile("HighSchool2013_proximity_net.csv.gz", SOCIOPATTERNS_URL)


def file_matches(path: Path, remote: RemoteFile) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    size = path.stat().st_size
    if remote.size is not None and size != remote.size:
        return False
    if remote.size is None and size == 0:
        return False
    if remote.md5:
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "md5").hexdigest()
        return actual.lower() == remote.md5.lower()
    return True


def download_file(
    remote: RemoteFile,
    directory: str | Path,
    *,
    progress: Callable[[int, int | None], None] | None = None,
    session=None,
    attempts: int = 3,
) -> DownloadResult:
    """Skip matching local files; replace only after a complete, checked download.

    Where a publisher supplies no size/checksum, a nonempty local file is retained
    for schema validation rather than treated as verified scientific data.
    """
    if attempts < 1:
        raise ValueError("attempts must be positive")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / remote.name
    if destination.is_symlink():
        raise DownloadError("拒绝写入符号链接，请选择普通本地文件。")
    if file_matches(destination, remote):
        if progress:
            progress(destination.stat().st_size, destination.stat().st_size)
        return DownloadResult(destination, True, destination.stat().st_size)

    client = session or requests.Session()
    try:
        for attempt in range(attempts):
            temporary = None
            try:
                with client.get(
                    remote.download_url, stream=True, timeout=TIMEOUT,
                    headers={"Accept-Encoding": "identity"},
                ) as response:
                    response.raise_for_status()
                    length = response.headers.get("Content-Length")
                    total = remote.size if remote.size is not None else int(length) if length else None
                    digest = hashlib.md5()
                    written = 0
                    with tempfile.NamedTemporaryFile(
                        dir=directory, prefix=f".{remote.name}.", suffix=".part", delete=False
                    ) as handle:
                        temporary = Path(handle.name)
                        if progress:
                            progress(0, total)
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if not chunk:
                                continue
                            handle.write(chunk)
                            digest.update(chunk)
                            written += len(chunk)
                            if total is not None and written > total:
                                raise ValueError("下载内容超过声明的文件大小。")
                            if progress:
                                progress(written, total)
                    if total is not None and written != total:
                        raise ValueError(f"文件大小不匹配：预期 {total}，实际 {written}。")
                    if remote.md5 and digest.hexdigest().lower() != remote.md5.lower():
                        raise ValueError("MD5 校验失败。")
                    if written == 0:
                        raise ValueError("下载文件为空。")
                    os.replace(temporary, destination)
                    return DownloadResult(destination, False, written)
            except (requests.RequestException, OSError, ValueError) as exc:
                if attempt + 1 == attempts:
                    raise DownloadError(f"{remote.name} 下载失败：{exc}。可重试或手动上传；原有文件已保留。") from exc
                time.sleep(0.2 * (attempt + 1))
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    finally:
        if session is None:
            client.close()


def save_upload(stream: BinaryIO, name: str, directory: str | Path) -> Path:
    """Save in bounded chunks; never silently overwrite an existing local file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / safe_name(name)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"{name} 已存在。请先检查本地文件；上传不会覆盖现有数据。")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as handle:
            temporary = Path(handle.name)
            while chunk := stream.read(CHUNK_SIZE):
                handle.write(chunk)
        if temporary.stat().st_size == 0:
            raise ValueError("上传文件为空。")
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def scan_local_files(directory: str | Path) -> list[dict]:
    directory = Path(directory)
    if not directory.exists():
        return []
    return [
        {"文件": path.name, "字节": path.stat().st_size, "状态": "Downloaded · 待验证"}
        for path in sorted(directory.iterdir())
        if path.is_file() and not path.is_symlink() and not path.name.startswith(".") and path.suffix != ".part"
    ]
