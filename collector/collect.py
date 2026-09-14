# -*- coding: utf-8 -*-
"""
멍BTI × 보호견 노출 채널 — 전국 공고 수집기 (GitHub Actions에서 매일 실행)

국가동물보호정보시스템 구조동물 조회 서비스(data.go.kr 15098931)에서
보호중인 개 공고를 시도별로 수집해 site/data/ 에 정적 JSON을 만든다.

사용법: python collector/collect.py --key "$ANIMAL_API_KEY" [--out site/data] [--days 60]
표준 라이브러리만 사용. 성향 태그 사전은 실측 킷 v1(2026-09-01)과 동일 — docs/SPEC_v0.md §4.
"""

import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

BASE_V2 = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2"
BASE_V1 = "https://apis.data.go.kr/1543061/abandonmentPublicSrvc"
OPS = {
    "v2": (BASE_V2 + "/abandonmentPublic_v2", BASE_V2 + "/sido_v2", BASE_V2 + "/sigungu_v2"),
    "v1": (BASE_V1 + "/abandonmentPublic", BASE_V1 + "/sido", BASE_V1 + "/sigungu"),
}
UPKIND_DOG = "417000"
KST = dt.timezone(dt.timedelta(hours=9))

TRAITS = {
    "온순·친화": ["온순", "순함", "순한", "순둥", "얌전", "친화", "사람을 좋아", "사람 좋아",
               "사람좋아", "애교", "친근", "잘 따", "잘따", "손을 타", "안기"],
    "활발": ["활발", "명랑", "에너지", "활동적", "장난"],
    "겁·경계": ["겁", "경계", "예민", "소심", "낯가림", "낯을 가", "무서워", "떨고", "숨으"],
    "입질·공격성": ["입질", "공격", "사나움", "사나운", "물려", "물음", "무는", "물기"],
    "짖음": ["짖"],
}


def build_url(endpoint, key, params):
    enc_key = key if "%" in key else urllib.parse.quote(key, safe="")
    return f"{endpoint}?serviceKey={enc_key}&{urllib.parse.urlencode(params)}"


def call_api(endpoint, key, params, retries=3):
    url = build_url(endpoint, key, dict(params, _type="json"))
    ctx = ssl.create_default_context()
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=40, context=ctx) as r:
                raw = r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last = f"요청 실패: {e}"
            time.sleep(2 * (attempt + 1))
            continue
        if raw.lstrip().startswith("<"):
            m = re.search(r"<returnAuthMsg>([^<]+)</returnAuthMsg>", raw) or \
                re.search(r"<resultMsg>([^<]+)</resultMsg>", raw)
            last = f"API 오류: {m.group(1) if m else raw[:150]}"
            time.sleep(2 * (attempt + 1))
            continue
        try:
            data = json.loads(raw)
        except Exception:
            last = f"JSON 파싱 실패: {raw[:150]}"
            continue
        header = data.get("response", {}).get("header", {})
        code = str(header.get("resultCode", ""))
        if code not in ("00", "0", ""):
            last = f"resultCode={code} {header.get('resultMsg')}"
            time.sleep(2 * (attempt + 1))
            continue
        return data.get("response", {}).get("body", {}), None
    return None, last


def items_of(body):
    if not isinstance(body, dict):
        return []
    items = body.get("items")
    if isinstance(items, dict):
        item = items.get("item", [])
        return item if isinstance(item, list) else [item]
    return items if isinstance(items, list) else []


def get(it, *keys):
    for k in keys:
        v = it.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def extract_traits(mark):
    return [t for t, kws in TRAITS.items() if any(k in mark for k in kws)]


def slim(it):
    mark = get(it, "specialMark")
    return {
        "id": get(it, "desertionNo"),
        "kind": get(it, "kindNm", "kindCd").replace("[개] ", ""),
        "age": get(it, "age"),
        "weight": get(it, "weight"),
        "sex": get(it, "sexCd"),
        "neuter": get(it, "neuterYn"),
        "mark": mark,
        "traits": extract_traits(mark),
        "care": get(it, "careNm"),
        "tel": get(it, "careTel"),
        "addr": get(it, "careAddr"),
        "org": get(it, "orgNm"),
        "until": get(it, "noticeEdt"),
        "state": get(it, "processState"),
        "img": get(it, "popfile1", "popfile"),
    }


def fetch_region(animal_ep, key, upr_cd, days, max_rows=5000):
    today = dt.datetime.now(KST).date()
    base = {
        "upkind": UPKIND_DOG,
        "upr_cd": upr_cd,
        "bgnde": (today - dt.timedelta(days=days)).strftime("%Y%m%d"),
        "endde": today.strftime("%Y%m%d"),
        "numOfRows": 100,
    }
    rows, page = [], 1
    while len(rows) < max_rows:
        body, err = call_api(animal_ep, key, dict(base, pageNo=page))
        if body is None:
            print(f"    [경고] upr_cd={upr_cd} p{page}: {err}", file=sys.stderr)
            break
        batch = items_of(body)
        if not batch:
            break
        rows.extend(batch)
        page += 1
        time.sleep(0.15)
    # 노출 채널이므로 종료(입양·반환 등 종결)건 제외 — 보호중·공고중만
    live = [it for it in rows if "보호중" in get(it, "processState") or "공고" in get(it, "processState")]
    return live if live else rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("ANIMAL_API_KEY", ""))
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--days", type=int, default=60)
    args = ap.parse_args()
    # Secret 붙여넣기 때 딸려온 공백·줄바꿈 제거 (2026-09-14 첫 실행 실패 원인)
    args.key = "".join(args.key.split())
    if not args.key:
        sys.exit("[중단] --key 또는 환경변수 ANIMAL_API_KEY 필요")

    # 1) 버전 판별 + 시도 목록
    ver, ops, sido_items = None, None, []
    for v in ("v2", "v1"):
        body, err = call_api(OPS[v][1], args.key, {"numOfRows": 30, "pageNo": 1})
        if body is not None and items_of(body):
            ver, ops, sido_items = v, OPS[v], items_of(body)
            break
        print(f"[정보] {v} 시도 목록 실패: {err}", file=sys.stderr)
    if not ver:
        sys.exit("[중단] v2/v1 모두 실패 — 키·엔드포인트 확인")
    animal_ep, _, sigungu_ep = ops
    print(f"[1/3] API {ver} · 시도 {len(sido_items)}곳")

    # 2) 시도별 수집
    os.makedirs(os.path.join(args.out, "regions"), exist_ok=True)
    index = {"updated": dt.datetime.now(KST).isoformat(timespec="seconds"), "total": 0, "sido": []}
    for s in sido_items:
        code = get(s, "orgCd", "org_cd")
        name = get(s, "orgdownNm", "orgNm")
        if not code:
            continue
        rows = [slim(it) for it in fetch_region(animal_ep, args.key, code, args.days)]
        # 시군구 목록 + 관할별 건수
        body, _ = call_api(sigungu_ep, args.key, {"upr_cd": code, "numOfRows": 200, "pageNo": 1})
        sig = []
        for g in items_of(body):
            gname = get(g, "orgdownNm", "orgNm")
            if not gname:
                continue
            cnt = sum(1 for r in rows if gname in r["org"])
            sig.append({"code": get(g, "orgCd", "org_cd"), "name": gname, "count": cnt})
        with open(os.path.join(args.out, "regions", f"{code}.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
        index["sido"].append({"code": code, "name": name, "count": len(rows), "sigungu": sig})
        index["total"] += len(rows)
        print(f"  {name}: {len(rows)}건")
        time.sleep(0.2)

    # 3) 인덱스 저장 + 최소 건수 검증
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[3/3] 완료 — 전국 {index['total']}건")
    if index["total"] < 100:
        sys.exit(f"[중단] 전국 {index['total']}건은 비정상 — 배포하지 않음 (API·키 점검)")


if __name__ == "__main__":
    main()
