#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cafe24 Admin API 추출기 (marun5 → Shopify JP 이관용)
=====================================================
표준 라이브러리만 사용. 설치 불필요. Python 3.8+

이 스크립트는 Claude 클라우드 컨테이너가 아니라 **발주자/개발자 로컬 PC**에서 실행한다.
(클라우드 컨테이너는 *.cafe24api.com 이 네트워크 허용목록에 없어 차단됨)

사용 순서
---------
  0) developers.cafe24.com 에서 앱 생성
     - Redirect URL 에 http://localhost:8724/callback 등록
     - Scope 체크: mall.read_product, mall.read_category, mall.read_store,
                   mall.read_community, mall.read_order (필요 시)
     - Client ID / Client Secret 확보

  1) 인증 (브라우저 1회)
     python cafe24_extract.py auth --mall marun5 --client-id XXX --client-secret YYY

  2) 추출
     python cafe24_extract.py pull --mall marun5 --out ./cafe24_dump

산출물 (./cafe24_dump/)
  categories.json     카테고리 전수
  products.json       상품 전수 (요약 필드)
  variants.json       Variant(옵션 조합)·재고·SKU
  options.json        상품별 옵션 정의
  reviews.json        상품 리뷰 게시판 (--board 로 번호 지정)
  products.csv        Shopify 매핑용 평면 CSV
  variants.csv        Shopify 매핑용 평면 CSV
  _meta.json          추출 시각·건수·API 버전

토큰은 .cafe24_token.json 에 저장되며 만료 시 자동 갱신한다.
"""

import argparse
import base64
import csv
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

TOKEN_FILE = ".cafe24_token.json"
API_VERSION = "2025-06-01"          # 개발자센터에 표시된 버전으로 맞출 것
REDIRECT_URI = "http://localhost:8724/callback"
SCOPES = [
    "mall.read_store",
    "mall.read_category",
    "mall.read_product",
    "mall.read_community",
]
PAGE = 100          # Cafe24 limit 최대 100
SLEEP = 0.35        # 초당 호출 제한 여유


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
def _request(method, url, headers=None, data=None, timeout=30):
    req = urllib.request.Request(url, method=method, data=data)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except urllib.error.URLError as e:
        raise SystemExit(
            f"\n[네트워크 차단] {url}\n  → {e}\n"
            "  이 머신에서 *.cafe24api.com 으로 나가는 트래픽이 막혀 있습니다.\n"
            "  방화벽/프록시/사내망 정책을 확인하세요.\n"
        )


def _basic(client_id, client_secret):
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


# ----------------------------------------------------------------------------
# OAuth
# ----------------------------------------------------------------------------
class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        q = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(q)
        _CallbackHandler.code = (params.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = _CallbackHandler.code is not None
        msg = "인증 완료. 이 창을 닫고 터미널로 돌아가세요." if ok else "인증 실패. code 파라미터가 없습니다."
        self.wfile.write(
            f"<html><body style='font-family:sans-serif;padding:60px'>"
            f"<h2>{msg}</h2></body></html>".encode("utf-8")
        )

    def log_message(self, *a):
        pass


def cmd_auth(args):
    state = base64.urlsafe_b64encode(os.urandom(9)).decode()
    q = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": args.client_id,
        "state": state,
        "redirect_uri": args.redirect_uri,
        "scope": ",".join(args.scope),
    })
    auth_url = f"https://{args.mall}.cafe24api.com/api/v2/oauth/authorize?{q}"

    print("\n[1/2] 브라우저에서 아래 URL 을 열어 승인하세요.\n")
    print(auth_url + "\n")

    port = urllib.parse.urlparse(args.redirect_uri).port or 8724
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), _CallbackHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print(f"    로컬 {port} 포트에서 콜백 대기 중… (Ctrl+C 로 중단)")
    deadline = time.time() + 300
    while _CallbackHandler.code is None and time.time() < deadline:
        time.sleep(0.4)
    httpd.shutdown()

    if not _CallbackHandler.code:
        raise SystemExit("인증 코드를 받지 못했습니다. Redirect URL 등록값을 확인하세요.")

    print("[2/2] 토큰 교환 중…")
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": _CallbackHandler.code,
        "redirect_uri": args.redirect_uri,
    }).encode()
    status, tok = _request(
        "POST",
        f"https://{args.mall}.cafe24api.com/api/v2/oauth/token",
        headers={
            "Authorization": _basic(args.client_id, args.client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body,
    )
    if status != 200:
        raise SystemExit(f"토큰 발급 실패 ({status}): {tok}")

    tok["_mall"] = args.mall
    tok["_client_id"] = args.client_id
    tok["_client_secret"] = args.client_secret
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tok, f, ensure_ascii=False, indent=1)
    os.chmod(TOKEN_FILE, 0o600)
    print(f"\n완료. {TOKEN_FILE} 저장됨. 이제 pull 을 실행하세요.\n")


def _load_token():
    if not os.path.exists(TOKEN_FILE):
        raise SystemExit(f"{TOKEN_FILE} 이 없습니다. 먼저 auth 를 실행하세요.")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return json.load(f)


def _refresh(tok):
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    }).encode()
    status, new = _request(
        "POST",
        f"https://{tok['_mall']}.cafe24api.com/api/v2/oauth/token",
        headers={
            "Authorization": _basic(tok["_client_id"], tok["_client_secret"]),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body,
    )
    if status != 200:
        raise SystemExit(f"토큰 갱신 실패 ({status}): {new}\n→ auth 를 다시 실행하세요.")
    new.update({k: tok[k] for k in ("_mall", "_client_id", "_client_secret")})
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    return new


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------
class Cafe24:
    def __init__(self, tok, api_version):
        self.tok = tok
        self.v = api_version
        self.base = f"https://{tok['_mall']}.cafe24api.com/api/v2/admin"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.tok['access_token']}",
            "Content-Type": "application/json",
            "X-Cafe24-Api-Version": self.v,
        }

    def get(self, path, **params):
        url = f"{self.base}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        status, data = _request("GET", url, headers=self._headers())
        if status == 401:
            self.tok = _refresh(self.tok)
            status, data = _request("GET", url, headers=self._headers())
        if status != 200:
            print(f"  ! {status} {path} {params} → {str(data)[:200]}", file=sys.stderr)
            return None
        return data

    def paged(self, path, key, **params):
        """limit/offset 페이징을 끝까지 순회."""
        out, offset = [], 0
        while True:
            data = self.get(path, limit=PAGE, offset=offset, **params)
            if not data:
                break
            chunk = data.get(key) or []
            out.extend(chunk)
            if len(chunk) < PAGE:
                break
            offset += PAGE
            print(f"    …{len(out)}건", end="\r", flush=True)
            time.sleep(SLEEP)
        return out


# ----------------------------------------------------------------------------
# pull
# ----------------------------------------------------------------------------
def cmd_pull(args):
    tok = _load_token()
    if args.mall and args.mall != tok["_mall"]:
        raise SystemExit(f"토큰은 '{tok['_mall']}' 몰의 것입니다.")
    api = Cafe24(tok, args.api_version)
    out = args.out
    os.makedirs(out, exist_ok=True)

    def dump(name, obj):
        p = os.path.join(out, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print(f"  → {name}  ({len(obj) if isinstance(obj, list) else 1}건)")

    print("\n[1] 카테고리")
    categories = api.paged("categories", "categories")
    dump("categories.json", categories)

    print("[2] 상품")
    products = api.paged("products", "products")
    dump("products.json", products)

    nos = [p.get("product_no") for p in products if p.get("product_no")]
    if args.only:
        keep = set(int(x) for x in args.only.split(","))
        nos = [n for n in nos if n in keep]
        print(f"    (--only 지정: {len(nos)}건으로 제한)")

    print(f"[3] Variant · 재고  ({len(nos)}개 상품)")
    variants = []
    for i, n in enumerate(nos, 1):
        d = api.get(f"products/{n}/variants", limit=PAGE)
        for v in (d or {}).get("variants", []):
            v["product_no"] = n
            variants.append(v)
        if i % 10 == 0:
            print(f"    {i}/{len(nos)}", end="\r", flush=True)
        time.sleep(SLEEP)
    dump("variants.json", variants)

    print(f"[4] 옵션 정의  ({len(nos)}개 상품)")
    options = []
    for i, n in enumerate(nos, 1):
        d = api.get(f"products/{n}/options")
        if d and d.get("options"):
            o = d["options"]
            o["product_no"] = n
            options.append(o)
        if i % 10 == 0:
            print(f"    {i}/{len(nos)}", end="\r", flush=True)
        time.sleep(SLEEP)
    dump("options.json", options)

    reviews = []
    if args.board:
        print(f"[5] 리뷰 게시판 board_no={args.board}")
        reviews = api.paged(f"boards/{args.board}/articles", "articles")
        dump("reviews.json", reviews)

    # ---- 평면 CSV ----
    print("[6] CSV 변환")
    pcols = ["product_no", "product_code", "product_name", "eng_product_name", "model_name",
             "price", "retail_price", "supply_price", "display", "selling",
             "made_in_code", "origin_place_value", "weight",
             "summary_description", "product_tag", "category_no"]
    with open(os.path.join(out, "products.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(pcols)
        for p in products:
            row = []
            for c in pcols:
                v = p.get(c, "")
                if c == "category_no":
                    v = "|".join(str(x.get("category_no")) for x in (p.get("category") or []))
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                row.append(v)
            w.writerow(row)

    vcols = ["product_no", "variant_code", "options", "display", "selling",
             "additional_amount", "quantity", "safety_inventory", "use_inventory"]
    with open(os.path.join(out, "variants.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(vcols)
        for v in variants:
            row = []
            for c in vcols:
                val = v.get(c, "")
                if c == "options":
                    val = " / ".join(
                        f"{o.get('name')}:{o.get('value')}" for o in (v.get("options") or [])
                    )
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
            w.writerow(row)

    meta = {
        "mall": tok["_mall"],
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "api_version": args.api_version,
        "counts": {
            "categories": len(categories),
            "products": len(products),
            "variants": len(variants),
            "options": len(options),
            "reviews": len(reviews),
        },
    }
    dump("_meta.json", meta)
    print(f"\n완료 → {os.path.abspath(out)}")
    print("  이 폴더를 zip 으로 묶어 Claude 대화창에 첨부하면 정규화·Shopify 투입을 이어서 진행합니다.\n")


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Cafe24 Admin API 추출기")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth", help="OAuth 인증 후 토큰 저장")
    a.add_argument("--mall", required=True, help="mall_id (예: marun5)")
    a.add_argument("--client-id", required=True)
    a.add_argument("--client-secret", required=True)
    a.add_argument("--redirect-uri", default=REDIRECT_URI)
    a.add_argument("--scope", nargs="*", default=SCOPES)
    a.set_defaults(func=cmd_auth)

    p = sub.add_parser("pull", help="데이터 추출")
    p.add_argument("--mall", default=None)
    p.add_argument("--out", default="./cafe24_dump")
    p.add_argument("--api-version", default=API_VERSION)
    p.add_argument("--board", type=int, default=4, help="리뷰 게시판 번호 (0이면 생략)")
    p.add_argument("--only", default=None, help="특정 product_no 만 (쉼표 구분)")
    p.set_defaults(func=cmd_pull)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
