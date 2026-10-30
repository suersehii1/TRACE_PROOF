"""한국어 여성 신경망 음성과 문장 경계 자막을 생성한다. 원본 고객 자료는 보내지 않는다."""
import asyncio
import json
import os
import subprocess
import wave
from pathlib import Path
import edge_tts
import imageio_ffmpeg

PROJECT = Path(__file__).resolve().parents[2]
WORK = PROJECT.parent / 'tmp' / 'sales_video'
WORK.mkdir(parents=True, exist_ok=True)
VOICE = 'ko-KR-SunHiNeural'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


async def synthesize(scene, semaphore):
    async with semaphore:
        mp3 = WORK / (scene['id'] + '.mp3')
        wav = WORK / (scene['id'] + '.wav')
        boundaries = []
        for attempt in range(3):
            try:
                boundaries = []
                communicator = edge_tts.Communicate(scene['narration'], VOICE, rate='-3%', boundary='SentenceBoundary')
                with mp3.open('wb') as output:
                    async for event in communicator.stream():
                        if event['type'] == 'audio':
                            output.write(event['data'])
                        elif event['type'] in ('SentenceBoundary', 'WordBoundary'):
                            boundaries.append(dict(start=event['offset'] / 10000000,
                                                   end=(event['offset'] + event['duration']) / 10000000,
                                                   text=event['text']))
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2)
        subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3),
                        '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)], check=True)
        with wave.open(str(wav)) as source:
            seconds = source.getnframes() / source.getframerate()
        scene.update(voice=VOICE, voice_gender='Female', voice_seconds=seconds,
                     duration=round(seconds + 1.6, 3), subtitle_boundaries=boundaries)
        print(scene['id'], round(seconds, 2), 'seconds', flush=True)
        return scene


async def main():
    scenes = json.loads((PROJECT / 'scripts/video/storyboard.json').read_text(encoding='utf-8'))
    voice_info = next(v for v in await edge_tts.list_voices() if v['ShortName'] == VOICE)
    if voice_info['Gender'] != 'Female':
        raise RuntimeError('여성 음성 설정을 확인할 수 없습니다.')
    (WORK / 'voice.json').write_text(json.dumps(voice_info, ensure_ascii=False, indent=2), encoding='utf-8')
    semaphore = asyncio.Semaphore(2)
    scenes = await asyncio.gather(*(synthesize(scene, semaphore) for scene in scenes))
    (WORK / 'timing.json').write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding='utf-8')
    print('TOTAL', round(sum(s['duration'] for s in scenes), 2), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
