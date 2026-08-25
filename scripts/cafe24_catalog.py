#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cafe24 Catalog MCP 클라이언트 — marun5(m5m5m5) 상품 수집
=========================================================
엔드포인트 : https://mcp-catalog.cafe24.com/api/mcp   (인증 불필요)
사용 툴     : search-products-detail(mall_id, product_no, shop_no)

Admin API 가 아니라 공개 카탈로그 MCP 이므로 다음만 얻을 수 있다:
  product_name / product_code / price / product_tag / 이미지 / product_url
  variants_simple (옵션 조합·재고) — **최대 5건까지만 반환됨**

얻을 수 없는 것(= Admin API 필요):
  전체 variant, 원산지, 소재 조성비, 상세페이지 HTML, 리뷰, 판매데이터, 카테고리 소속
"""
import csv, json, os, re, sys, time, urllib.error, urllib.request

URL = "https://mcp-catalog.cafe24.com/api/mcp"
MALL = "m5m5m5"


class CatalogMCP:
    def __init__(self, url=URL):
        self.url, self.sid, self.n = url, None, 0
        self._init()

    def _rpc(self, method, params=None, notify=False, timeout=60):
        self.n += 1
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = self.n
        if params is not None:
            body["params"] = params
        req = urllib.request.Request(self.url, method="POST",
                                     data=json.dumps(body).encode())
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.sid:
            req.add_header("Mcp-Session-Id", self.sid)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                self.sid = r.headers.get("Mcp-Session-Id") or self.sid
                raw = r.read().decode()
        except urllib.error.HTTPError as e:
            return {"error": {"message": f"HTTP {e.code}: {e.read().decode()[:200]}"}}
        except urllib.error.URLError as e:
            return {"error": {"message": f"NETWORK: {e}"}}
        if not raw.strip():
            return {}
        if raw.lstrip()[:6] in ("event:", "data: ") or raw.lstrip().startswith("data:"):
            for line in raw.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
        return json.loads(raw)

    def _init(self):
        self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "marun5-jp", "version": "1.0"}})
        self._rpc("notifications/initialized", {}, notify=True)

    def call(self, name, args):
        r = self._rpc("tools/call", {"name": name, "arguments": args})
        if r.get("error"):
            return None, r["error"].get("message", "unknown")
        content = (r.get("result") or {}).get("content") or []
        if not content:
            return None, "empty content"
        try:
            return json.loads(content[0].get("text", "")), None
        except json.JSONDecodeError:
            return content[0].get("text", ""), None

    def detail(self, product_no, mall=MALL, shop_no=1):
        return self.call("search-products-detail",
                         {"mall_id": mall, "product_no": str(product_no), "shop_no": shop_no})


# ---------------------------------------------------------------------------
def split_options(opt: str):
    """'[10%] 4매입-스킨 4매-S' → (할인표기, ['4매입','스킨 4매','S'])"""
    if not opt:
        return "", []
    disc = ""
    m = re.match(r"^\s*(\[[^\]]+\])\s*", opt)
    if m:
        disc = m.group(1)
        opt = opt[m.end():]
    return disc, [p.strip() for p in opt.split("-") if p.strip()]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "mvp41.csv"
    out = sys.argv[2] if len(sys.argv) > 2 else "cafe24_catalog_dump"
    os.makedirs(out, exist_ok=True)

    targets = []
    with open(src, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("product_no"):
                targets.append(row)
    print(f"대상 {len(targets)}건 · mall_id={MALL}\n")

    mcp = CatalogMCP()
    got, miss, rows, vrows = [], [], [], []

    for i, t in enumerate(targets, 1):
        pno = t["product_no"]
        d, err = mcp.detail(pno)
        if err or not isinstance(d, dict):
            miss.append({**t, "error": err})
            print(f"  {i:2}/{len(targets)}  {pno:>5}  ✗ {err}")
            time.sleep(0.3)
            continue
        d["_sheet"] = t
        got.append(d)

        axes = []
        for v in d.get("variants_simple") or []:
            disc, parts = split_options(v.get("options", ""))
            for j, p in enumerate(parts):
                while len(axes) <= j:
                    axes.append(set())
                axes[j].add(p)
            vrows.append({
                "product_no": d.get("product_no"),
                "product_code": d.get("product_code"),
                "variant_code": v.get("variant_code"),
                "discount_tag": disc,
                "options_raw": v.get("options"),
                "opt1": parts[0] if len(parts) > 0 else "",
                "opt2": parts[1] if len(parts) > 1 else "",
                "opt3": parts[2] if len(parts) > 2 else "",
                "opt4": parts[3] if len(parts) > 3 else "",
                "quantity": v.get("quantity"),
                "display": v.get("display"),
                "selling": v.get("selling"),
            })

        rows.append({
            "카테고리": t.get("카테고리", ""),
            "PI코드": t.get("PI코드", ""),
            "product_no": d.get("product_no"),
            "product_code": d.get("product_code"),
            "product_name": d.get("product_name"),
            "price_krw": d.get("price"),
            "price_display": d.get("product_price_display"),
            "sold_out": d.get("sold_out"),
            "option_axes": len(axes),
            "axis_sample": " | ".join("/".join(sorted(a)[:4]) for a in axes),
            "variants_returned": len(d.get("variants_simple") or []),
            "tag_count": len(d.get("product_tag") or []),
            "tags": ", ".join(d.get("product_tag") or []),
            "small_image": d.get("small_image"),
            "detail_image": d.get("detail_image"),
            "product_url": d.get("product_url"),
        })
        print(f"  {i:2}/{len(targets)}  {pno:>5}  {d.get('product_name','')[:32]:<34} "
              f"₩{int(float(d.get('price') or 0)):>7,}  축{len(axes)}  var{len(d.get('variants_simple') or [])}")
        time.sleep(0.3)

    json.dump(got, open(f"{out}/details.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    if miss:
        json.dump(miss, open(f"{out}/missing.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    if rows:
        with open(f"{out}/products.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    if vrows:
        with open(f"{out}/variants.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(vrows[0].keys()))
            w.writeheader(); w.writerows(vrows)

    print(f"\n성공 {len(got)} / 실패 {len(miss)}  →  {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
