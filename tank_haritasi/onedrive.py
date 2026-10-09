"""OneDrive dosya işlemleri (yalnızca okuma / yeni oluşturma / yerine koyma — silme YOK)."""
from __future__ import annotations

import hashlib
import urllib.parse

from .graph import GraphClient, GraphError

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SELECT = "id,name,eTag,cTag,size,lastModifiedDateTime,file,folder,webUrl"
SIMPLE_UPLOAD_LIMIT = 4_000_000
CHUNK = 320 * 1024 * 10  # 320 KiB'nin katı


class ConflictError(RuntimeError):
    """Dosya, biz okuduktan sonra başkası tarafından değiştirildi (If-Match / 412)."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _root_path(path: str) -> str:
    return "/me/drive/root:/" + urllib.parse.quote(path.strip("/"), safe="/")


def get_item_by_path(c: GraphClient, path: str) -> dict:
    return c.request("GET", _root_path(path), params={"$select": SELECT}).json()


def get_item(c: GraphClient, item_id: str) -> dict:
    return c.request("GET", f"/me/drive/items/{item_id}", params={"$select": SELECT}).json()


def download(c: GraphClient, item_id: str) -> bytes:
    return c.request("GET", f"/me/drive/items/{item_id}/content").content


def download_consistent(c: GraphClient, path: str, attempts: int = 3) -> tuple[dict, bytes]:
    """Bellekte tutulan içeriğin gerçekten meta'daki eTag'e ait olduğundan emin ol."""
    for _ in range(attempts):
        before = get_item_by_path(c, path)
        if "file" not in before:
            raise GraphError(400, "notAFile", f"{path} bir dosya değil.")
        data = download(c, before["id"])
        after = get_item(c, before["id"])
        if before["eTag"] == after["eTag"]:
            return before, data
    raise ConflictError("Dosya okunurken sürekli değişiyor; biraz sonra tekrar deneyin.")


def ensure_folder(c: GraphClient, folder: str) -> dict:
    try:
        item = get_item_by_path(c, folder)
    except GraphError as e:
        if e.status != 404:
            raise
        parent, _, name = folder.strip("/").rpartition("/")
        endpoint = f"/me/drive/root:/{urllib.parse.quote(parent, safe='/')}:/children" if parent else "/me/drive/root/children"
        try:
            item = c.request("POST", endpoint, json={
                "name": name, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"}).json()
        except GraphError as e2:
            if e2.status != 409:
                raise
            item = get_item_by_path(c, folder)
    if "folder" not in item:
        raise GraphError(409, "notAFolder", f"'{folder}' bir klasör değil.")
    return item


def upload_new(c: GraphClient, folder: str, name: str, data: bytes) -> dict:
    """Yeni dosya oluşturur; aynı adlı dosya varsa ASLA üzerine yazmaz (conflictBehavior=fail)."""
    target = _root_path(f"{folder}/{name}")
    if len(data) <= SIMPLE_UPLOAD_LIMIT:
        return c.request("PUT", f"{target}:/content", params={"@microsoft.graph.conflictBehavior": "fail"},
                         headers={"Content-Type": XLSX_MIME}, data=data).json()
    sess = c.request("POST", f"{target}:/createUploadSession",
                     json={"item": {"@microsoft.graph.conflictBehavior": "fail"}}).json()
    return _upload_chunks(c, sess["uploadUrl"], data)


def upload_replace(c: GraphClient, item_id: str, data: bytes, etag: str) -> dict:
    """Var olan dosyanın içeriğini yalnızca eTag hâlâ aynıysa değiştirir (If-Match)."""
    hdr = {"If-Match": etag}
    try:
        if len(data) <= SIMPLE_UPLOAD_LIMIT:
            return c.request("PUT", f"/me/drive/items/{item_id}/content",
                             headers={**hdr, "Content-Type": XLSX_MIME}, data=data).json()
        sess = c.request("POST", f"/me/drive/items/{item_id}/createUploadSession", headers=hdr,
                         json={"item": {"@microsoft.graph.conflictBehavior": "replace"}}).json()
        return _upload_chunks(c, sess["uploadUrl"], data)
    except GraphError as e:
        if e.status == 412:
            raise ConflictError("Dosya siz okuduktan sonra değiştirilmiş (eTag uyuşmuyor). "
                                "Hiçbir şey yazılmadı; komutu yeniden çalıştırın.") from e
        raise


def _upload_chunks(c: GraphClient, url: str, data: bytes) -> dict:
    total, pos, last = len(data), 0, None
    while pos < total:
        part = data[pos:pos + CHUNK]
        last = c.put_upload_chunk(url, part, f"bytes {pos}-{pos + len(part) - 1}/{total}")
        pos += len(part)
    return last.json()
