"""완성 MP4를 끝까지 디코딩하고 장면별 확인 이미지와 음량 검증 기록을 남긴다."""
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

PROJECT = Path(__file__).resolve().parents[2]
WORK = PROJECT.parent / 'tmp/sales_video'
DOCS = PROJECT / 'docs'
VIDEO = DOCS / 'TraceProof_고객시연_여성내레이션.mp4'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    return subprocess.run([FFMPEG, '-hide_banner', *args], capture_output=True, text=True, encoding='utf-8', errors='replace')


def main():
    metadata = json.loads((DOCS / 'TraceProof_고객시연_제작정보.json').read_text(encoding='utf-8'))
    probe = run(['-i', str(VIDEO)]).stderr
    if not all(term in probe for term in ['Video: h264', '1920x1080', 'Audio: aac']):
        raise RuntimeError('영상·음성 코덱 또는 해상도가 예상과 다릅니다.')
    decode = run(['-v', 'error', '-i', str(VIDEO), '-f', 'null', '-'])
    if decode.returncode != 0 or decode.stderr.strip():
        raise RuntimeError('영상 디코딩 오류: ' + decode.stderr)
    volume = run(['-i', str(VIDEO), '-vn', '-af', 'volumedetect', '-f', 'null', '-']).stderr
    mean = re.search(r'mean_volume: ([\-\d.]+) dB', volume)
    peak = re.search(r'max_volume: ([\-\d.]+) dB', volume)
    if not mean or float(mean[1]) < -35:
        raise RuntimeError('내레이션 음량이 너무 작거나 없습니다.')
    frames = []
    for i, chapter in enumerate(metadata['chapters']):
        moment = chapter['start'] + min(chapter['duration'] * 0.5, 9)
        path = WORK / f'qa-{i + 1:02d}.png'
        result = run(['-loglevel', 'error', '-y', '-ss', str(moment), '-i', str(VIDEO), '-frames:v', '1', str(path)])
        if result.returncode:
            raise RuntimeError(result.stderr)
        frames.append((chapter['chapter'], path))
    sheet = Image.new('RGB', (1440, 1410), '#dce5eb')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 17)
    for i, (label, path) in enumerate(frames):
        x, y = (i % 3) * 480, (i // 3) * 350
        image = Image.open(path).convert('RGB')
        image.thumbnail((472, 266))
        sheet.paste(image, (x + 4, y + 33))
        draw.text((x + 9, y + 8), f'{i + 1:02d} {label}', font=font, fill='#254357')
    sheet.save(WORK / 'qa-contact-sheet.jpg', quality=94)
    result = dict(full_decode='PASS', video_codec='H.264', audio_codec='AAC', resolution='1920x1080',
                  mean_volume_db=float(mean[1]), peak_volume_db=float(peak[1]) if peak else None,
                  scene_count=len(frames), voice_gender='Female', voice='ko-KR-SunHiNeural')
    (WORK / 'quality-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
