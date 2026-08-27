import os, time, hmac, hashlib
from urllib.parse import urlencode
import requests

BASE_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1"
HOST = "https://api-gateway.coupang.com"


def _auth(method: str, path_and_query: str) -> str:
    access = os.environ["COUPANG_ACCESS_KEY"]
    secret = os.environ["COUPANG_SECRET_KEY"]
    if "?" in path_and_query:
        path, query = path_and_query.split("?", 1)
    else:
        path, query = path_and_query, ""
    dt = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = dt + method.upper() + path + query
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access}, signed-date={dt}, signature={signature}"


def get(path: str, params: dict | None = None) -> dict:
    params = params or {}
    qs = urlencode(params, doseq=True)
    full_path = BASE_PATH + path + ("?" + qs if qs else "")
    r = requests.get(
        HOST + full_path,
        headers={"Authorization": _auth("GET", full_path), "Content-Type": "application/json"},
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    if str(data.get("rCode", "0")) != "0":
        raise RuntimeError(f"Coupang API error: {data}")
    return data


def search(keyword: str, limit: int = 10) -> list[dict]:
    sub_id = os.getenv("COUPANG_SUB_ID", "salpyeoon-v2")
    data = get("/products/search", {
        "keyword": keyword,
        "limit": min(limit, 10),
        "subId": sub_id,
        "imageSize": "512x512",
        "srpLinkOnly": "false",
    })
    return data.get("data", {}).get("productData", [])
