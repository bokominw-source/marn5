#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/details.json (Catalog MCP 원본 응답) → products/variants CSV 재생성
=======================================================================
네트워크 없이 동작한다. 원본 응답은 이미 저장돼 있으므로
파서를 고칠 때마다 이 스크립트로 CSV 를 다시 만들면 된다.

    python3 scripts/rebuild_from_details.py                 # data/ 를 제자리 갱신
    python3 scripts/rebuild_from_details.py out/            # 다른 곳에 쓰기

컬럼은 기존 CSV 스키마를 유지하되 `축역할` 을 추가한다.
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from options import classify_axes, normalize_value, split_options

# 100엔 = 873원 (2026-08-21). 참고 환산일 뿐 JPY 정가표가 아니다.
KRW_PER_100JPY = 873.0

P_COLS = ["카테고리", "PI코드", "product_no", "product_code", "product_name",
          "KRW", "JPY_환산", "축", "축구성", "축역할", "태그수", "sold_out",
          "image", "url"]
V_COLS = ["product_no", "product_code", "variant_code", "discount", "options_raw",
          "axes", "a1", "a2", "a3", "a4", "quantity", "display", "selling"]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "data")
    os.makedirs(out, exist_ok=True)

    details = json.load(open(os.path.join(root, "data", "details.json"), encoding="utf-8"))
    prows, vrows = [], []

    for d in details:
        sheet = d.get("_sheet") or {}
        parsed = [split_options(v.get("options", "")) for v in d.get("variants_simple") or []]
        axes = classify_axes([parts for _, parts in parsed if parts])

        for v, (disc, parts) in zip(d.get("variants_simple") or [], parsed):
            vals = [normalize_value(p) for p in parts]
            vrows.append({
                "product_no": d.get("product_no"),
                "product_code": d.get("product_code"),
                "variant_code": v.get("variant_code"),
                "discount": disc,
                "options_raw": v.get("options"),
                "axes": len(vals),
                "a1": vals[0] if len(vals) > 0 else "",
                "a2": vals[1] if len(vals) > 1 else "",
                "a3": vals[2] if len(vals) > 2 else "",
                "a4": vals[3] if len(vals) > 3 else "",
                "quantity": v.get("quantity"),
                "display": v.get("display"),
                "selling": v.get("selling"),
            })

        krw = int(float(d.get("price") or 0))
        prows.append({
            "카테고리": sheet.get("카테고리", ""),
            "PI코드": sheet.get("PI코드", ""),
            "product_no": d.get("product_no"),
            "product_code": d.get("product_code"),
            "product_name": d.get("product_name"),
            "KRW": krw,
            "JPY_환산": round(krw / KRW_PER_100JPY * 100),
            "축": len(axes),
            "축구성": " × ".join(f"{a['role']}({len(a['values'])})" for a in axes),
            "축역할": " × ".join(a["role"] for a in axes),
            "태그수": len(d.get("product_tag") or []),
            "sold_out": d.get("sold_out"),
            "image": d.get("small_image"),
            "url": d.get("product_url"),
        })

    for name, cols, rows in (("products_41.csv", P_COLS, prows),
                             ("variants_183.csv", V_COLS, vrows)):
        with open(os.path.join(out, name), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"  {name:<20} {len(rows):>4}행")

    n4 = [(p["product_no"], p["product_name"]) for p in prows if p["축"] > 3]
    print(f"\n상품 {len(prows)} · variant {len(vrows)}")
    print(f"4축 상품 {len(n4)}건: {n4}")
    capped = sum(1 for d in details if len(d.get('variants_simple') or []) == 5)
    print(f"⚠ variant 5건 상한에 걸린 상품 {capped}/{len(details)} — 실제 조합 수는 이보다 많다")


if __name__ == "__main__":
    main()
