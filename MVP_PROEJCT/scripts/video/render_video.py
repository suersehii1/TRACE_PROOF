"""실제 화면 녹화와 여성 내레이션을 1080p MP4로 편집하고 자막·미리보기를 만든다."""
import json
import math
import os
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

PROJECT = Path(__file__).resolve().parents[2]
WORK = PROJECT.parent / 'tmp/sales_video'
DOCS = PROJECT / 'docs'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = 'C:/Windows/Fonts/malgun.ttf'
BOLD_PATH = 'C:/Windows/Fonts/malgunbd.ttf'
OUTPUT = DOCS / 'TraceProof_고객시연_여성내레이션.mp4'


def font(size, bold=False):
    return ImageFont.truetype(BOLD_PATH if bold else FONT_PATH, size)


def media_info(path):
    process = subprocess.run([FFMPEG, '-hide_banner', '-i', str(path)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    match = re.search(r'Duration: (\d+):(\d+):([\d.]+)', process.stderr)
    if not match:
        raise RuntimeError('영상 길이를 확인할 수 없습니다: ' + str(path))
    return float(match[1]) * 3600 + float(match[2]) * 60 + float(match[3]), process.stderr


def stage_image(scene, index):
    image = Image.new('RGB', (1920, 1080), '#eef3f6')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((120, 21, 155, 56), 10, fill='#0d9386')
    draw.text((130, 23), 'T', font=font(23, True), fill='white')
    draw.text((167, 20), 'TraceProof', font=font(27, True), fill='#18374c')
    draw.text((360, 27), scene['chapter'], font=font(21), fill='#4d6b7c')
    draw.text((1640, 29), f'{index + 1:02d} / 12', font=font(18), fill='#638192')
    if scene['id'] == 'mobile':
        draw.rounded_rectangle((1161, 72, 1569, 934), 25, fill='#d5e0e6')
        draw.rounded_rectangle((1167, 77, 1563, 929), 20, fill='white')
        draw.text((164, 190), '현장에서도 같은 업무 흐름', font=font(24, True), fill='#19897b')
        draw.multiline_text((158, 258), '휴대폰에서\n데이터와 검토를\n확인하세요.', font=font(64, True), fill='#18374c', spacing=18)
        for line, y in [('같은 네트워크에서 접속', 590), ('원본과 검토 이력 확인', 654), ('실제 장비는 어댑터로 확장', 718)]:
            draw.ellipse((164, y + 8, 180, y + 24), fill='#159b8a')
            draw.text((202, y), line, font=font(27), fill='#69818f')
    else:
        draw.rounded_rectangle((115, 75, 1805, 946), 13, fill='#d9e4ea')
    draw.rounded_rectangle((120, 965, 1800, 1066), 11, fill='#132f43')
    draw.text((124, 943), '실제 MVP 화면과 가상 데이터로 제작한 고객 시연', font=font(12), fill='#8095a3')
    path = WORK / (scene['id'] + '-stage.png')
    image.save(path)
    return path


def timestamp(seconds, ass=False):
    if ass:
        ticks = round(seconds * 100)
        return f'{ticks // 360000}:{ticks // 6000 % 60:02d}:{ticks // 100 % 60:02d}.{ticks % 100:02d}'
    ticks = round(seconds * 1000)
    return f'{ticks // 3600000:02d}:{ticks // 60000 % 60:02d}:{ticks // 1000 % 60:02d},{ticks % 1000:03d}'


def wrap_caption(text):
    # 자막은 실제 문장 경계 시각을 사용하고, 긴 문장만 화면 폭 안에서 줄바꿈한다.
    measuring = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines, current = [], ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if current and measuring.textlength(candidate, font=font(33)) > 1510:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return '\n'.join(lines)


def make_subtitles(scene, offset, global_cues):
    ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Malgun Gothic,33,&H00FFFFFF,&H00FFFFFF,&H00132F43,&H00132F43,0,0,0,0,100,100,0,0,1,0,0,2,165,165,32,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    boundaries = scene['subtitle_boundaries']
    if not boundaries:
        raise RuntimeError('문장 경계 자막이 없습니다: ' + scene['id'])
    for i, cue in enumerate(boundaries):
        start = cue['start'] + 0.5
        end = min(cue['end'], boundaries[i + 1]['start'] - 0.02) + 0.5 if i + 1 < len(boundaries) else cue['end'] + 0.5
        text = wrap_caption(cue['text'])
        ass_text = text.replace('\\', '\\\\').replace('{', '').replace('}', '').replace('\n', r'\N')
        ass += f'Dialogue: 0,{timestamp(start, True)},{timestamp(end, True)},Default,,0,0,0,,{ass_text}\n'
        global_cues.append(dict(start=offset + start, end=offset + end, text=text))
    path = WORK / (scene['id'] + '.ass')
    path.write_text(ass, encoding='utf-8-sig')
    return path


def render_scene(scene, index, offset, global_cues):
    stage = stage_image(scene, index)
    make_subtitles(scene, offset, global_cues)
    source = WORK / 'clips' / (scene['id'] + '.webm')
    recorded_seconds, _ = media_info(source)
    duration = math.ceil(scene['duration'] * 30) / 30
    # 녹화 시작 전 화면 준비 구간을 제거하고 실제 시연 장면만 끝에서 잘라 사용한다.
    seek = max(0, recorded_seconds - scene['duration'])
    if scene['id'] == 'mobile':
        scale, placement = 'scale=390:844', 'overlay=1170:80'
    else:
        scale, placement = 'scale=1680:860', 'overlay=120:80'
    filters = f'[0:v]fps=30,{scale},setsar=1,tpad=stop_mode=clone:stop_duration=1[screen];[2:v][screen]{placement}:shortest=1[composed];[composed]ass={scene["id"]}.ass,format=yuv420p[v]'
    output = WORK / (scene['id'] + '-final.mp4')
    command = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(seek), '-i', str(source),
               '-i', str(WORK / (scene['id'] + '.wav')), '-loop', '1', '-i', str(stage),
               '-filter_complex', filters, '-map', '[v]', '-map', '1:a', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,adelay=500,apad',
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '21', '-r', '30', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
               '-t', str(duration), '-movflags', '+faststart', str(output)]
    subprocess.run(command, check=True, cwd=WORK)
    print('RENDERED', scene['id'], f'{duration:.2f}s', flush=True)
    return output, duration


def main():
    scenes = json.loads((WORK / 'timing.json').read_text(encoding='utf-8'))
    captures = json.loads((WORK / 'recordings.json').read_text(encoding='utf-8'))
    if len(captures) != len(scenes):
        raise RuntimeError('모든 시연 장면의 녹화가 끝나지 않았습니다.')
    clips, global_cues, timeline = [], [], []
    offset = 0
    only_scenes = set(os.getenv('RENDER_SCENES', '').split(',')) - {''}
    for i, scene in enumerate(scenes):
        if only_scenes and scene['id'] not in only_scenes:
            make_subtitles(scene, offset, global_cues)
            output = WORK / (scene['id'] + '-final.mp4')
            if not output.exists():
                raise RuntimeError('기존 편집 영상이 없습니다: ' + scene['id'])
            duration = math.ceil(scene['duration'] * 30) / 30
        else:
            output, duration = render_scene(scene, i, offset, global_cues)
        clips.append(output)
        timeline.append(dict(chapter=scene['chapter'], start=round(offset, 3), duration=round(duration, 3)))
        offset += duration
    listing = WORK / 'concat.txt'
    listing.write_text('\n'.join("file '" + clip.name + "'" for clip in clips), encoding='utf-8')
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-c', 'copy', '-movflags', '+faststart', str(OUTPUT)], check=True, cwd=WORK)
    srt = '\n\n'.join(f'{i + 1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i, c in enumerate(global_cues))
    (DOCS / 'TraceProof_고객시연_자막.srt').write_text(srt + '\n', encoding='utf-8-sig')
    poster = DOCS / 'TraceProof_고객시연_미리보기.jpg'
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-ss', '2', '-i', str(OUTPUT), '-frames:v', '1', '-q:v', '2', str(poster)], check=True)
    duration, probe = media_info(OUTPUT)
    metadata = dict(duration_seconds=round(duration, 3), resolution='1920x1080', fps=30, video_codec='H.264', audio_codec='AAC',
                    voice='ko-KR-SunHiNeural', gender='Female', language='ko-KR', subtitles='한국어 하드 자막 및 SRT',
                    size_bytes=OUTPUT.stat().st_size, chapters=timeline)
    (DOCS / 'TraceProof_고객시연_제작정보.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (WORK / 'final_probe.txt').write_text(probe, encoding='utf-8')
    script = '# 고객 시연 영상 대본과 장면 구성\n\n실제 실행 화면과 가상 데이터로 제작했습니다. 여성 합성 음성 ko-KR-SunHiNeural을 사용했습니다.\n\n'
    for scene, timing in zip(scenes, timeline):
        stamp = f'{int(timing["start"]) // 60:02d}:{int(timing["start"]) % 60:02d}'
        script += f'## {stamp} {scene["chapter"]}\n\n{scene["narration"]}\n\n'
    (DOCS / 'VIDEO_SCRIPT.md').write_text(script, encoding='utf-8')
    player = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TraceProof 고객 시연</title><style>body{font-family:system-ui,sans-serif;background:#112c40;color:#fff;margin:0;padding:32px 5vw}main{max-width:1400px;margin:auto}h1{font-size:26px}p{color:#abc5d2;font-size:14px;line-height:1.8}video{width:100%;border-radius:12px;background:#071a28}a{color:#80d3c1}</style><main><h1>TraceProof 고객 시연</h1><p>실제 MVP 화면 · 한국어 여성 내레이션 · 한국어 자막</p><video controls preload="metadata" poster="TraceProof_고객시연_미리보기.jpg"><source src="TraceProof_고객시연_여성내레이션.mp4" type="video/mp4"></video><p>가상 데이터를 사용한 기능 시연입니다. 고객 인수 합격 또는 수율 개선을 보장하지 않습니다.<br><a href="TraceProof_고객시연_여성내레이션.mp4" download>영상 다운로드</a> · <a href="VIDEO_SCRIPT.md">시연 대본</a></p></main></html>'''
    (DOCS / 'TraceProof_고객시연_재생.html').write_text(player, encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
