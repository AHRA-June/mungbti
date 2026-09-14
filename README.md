# 멍BTI × 보호견 노출 채널

전국 보호센터의 유기견 공고를 매일 자동 수집해, 사람들 눈에 띄는 세 개의 창으로 내보낸다.
**서버·DB 없음, 운영 비용 0원.** 상세 설계는 [docs/SPEC_v0.md](docs/SPEC_v0.md).

| 창 | 주소 (Pages 활성화 후) | 무엇 |
|---|---|---|
| 공고 페이지 | `/` | 지역 선택 → 보호견 카드 목록 |
| 결과 카드 embed | `/embed/card.js` | 멍BTI 결과 화면에 붙이는 "우리 동네 보호견" 위젯 |
| 예비입양 일지 | `/journal/` | 10일 체크리스트 + 인스타 공유 카드 생성기 |

```
공공데이터 API ─(매일 06:00 KST, GitHub Actions)→ collector/collect.py → site/data/*.json → GitHub Pages
```

## 최초 설정 (저장소 주인, 1회 · 5분)

1. **Secret 등록** — Settings → Secrets and variables → Actions → New repository secret
   - Name: `ANIMAL_API_KEY` / Value: 공공데이터포털 인증키 (데이터셋 15098931 활용신청)
2. **Pages 켜기** — Settings → Pages → Build and deployment → Source: **GitHub Actions**
3. Actions 탭 → `수집 후 Pages 배포` → **Run workflow** (첫 실행 수동, 이후 매일 자동)

## 멍BTI 쪽 연동 (결과 화면에 붙여넣기)

```html
<div id="mungbti-dogs"></div>
<script src="https://ahra-june.github.io/mungbti/embed/card.js"
        data-target="mungbti-dogs"
        data-sido="서울특별시"
        data-sigungu="동대문구"
        data-traits="온순·친화,활발"
        data-count="3"></script>
```

- `data-sido`/`data-sigungu`: 설문에서 받은 지역. `data-traits`: 결과 유형과 어울리는 성향 태그
  (`온순·친화` `활발` `겁·경계` `입질·공격성` `짖음` 중에서)
- 위젯은 오류 시 아무것도 그리지 않는다 — 호스트 페이지를 깨지 않음
- 미리보기: Pages 배포 후 `/embed/demo.html`

## 원칙

1. 성향 표시는 **보호센터 기재 인용** — 이 서비스의 평가·보증이 아니며, 모든 화면에 그 문구를 노출한다
2. 일지는 **판정이 아니라 관찰 기록** — 기록은 사용자 기기(localStorage)에만 저장된다
3. 서버·DB·계정을 도입하지 않는다 — 바뀌어야 한다면 docs/SPEC_v0.md부터 고친다

## 데이터 출처

농림축산검역본부 국가동물보호정보시스템 「구조동물 조회 서비스」 (공공데이터포털 15098931).
지자체 보호센터 공고 동물 한정 — 개인 임시보호 동물은 포함되지 않는다.
