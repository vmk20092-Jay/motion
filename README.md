# motion

키네틱 타이포그래피 모션그래픽 작업 모음. 영상, 배경음악, 화면 모두 Python 코드로 직접 생성했습니다.

## 01_november_autumn — 11월, 가을의 끝자락

| 파일 | 규격 | 설명 |
|---|---|---|
| `november_kinetic.mp4` | 1920×1080, 10초 | 가로형 원본 (음악 없음) |
| `november_reel.mp4` | 1080×1920, 10초 | 인스타그램 릴스용, 배경음악 포함 |
| `november_reel.html` | 9:16 | 브라우저 재생용 (음악·폰트 내장, 오프라인 재생) |

- 문구: 11월 → 바람이 조금 차가워지고 → 마음은 조금 더 따뜻해지는 → 가을, 그 끝자락에서
- 음악: 피아노·패드 앰비언트 직접 합성 (`src/bgm.py`)

## 02_chosun_recruit_reels — 조선일보 취준생 대상 회사 소개 릴스

| 파일 | 규격 | 설명 |
|---|---|---|
| `chosun_recruit_brand_30s.mp4` | 1080×1920, 30초 | **최종본** — 회사 소개 (기자·PD·미디어경영) |
| `drafts/chosun_reels_30s.mp4` | 1080×1920, 30초 | 초안: 대학생 대상 조선일보 구독 홍보 |
| `drafts/chosun_reels_jobseeker_30s.mp4` | 1080×1920, 30초 | 초안: 취준생 대상 조선일보 구독 홍보 |

- 글꼴: 조선일보명조 (조선일보사 무료 배포 글꼴)
- 음악: 120BPM 팝하우스 직접 합성, 글자 등장이 모두 0.5초 박자에 맞춰짐 (`src/music.py`)
- 집행 전 확인: "1000만 오디언스", "채용연계형" 문구는 사내 확인 필요

## 다시 만들기

```bash
pip install pillow numpy scipy          # ffmpeg 필요

# 01 가을 영상
cd 01_november_autumn/src
python3 bgm.py                           # bgm.wav
python3 reel.py render reel_v.mp4        # 세로 영상

# 02 조선일보 릴스 — src/fonts/ChosunNM.ttf (조선일보명조) 를 먼저 넣어주세요
cd 02_chosun_recruit_reels/src
python3 music.py                         # music.wav
python3 video.py render v.mp4
ffmpeg -i v.mp4 -i music.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
       -af loudnorm=I=-14:TP=-1.5 -shortest out.mp4
```

`python3 video.py test 1.6 7.3 15.5` 처럼 실행하면 해당 시점 프레임만 이미지로 뽑아 미리 볼 수 있습니다.
