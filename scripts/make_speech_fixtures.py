"""Optional Vietnamese synthetic speech fixtures; requires network, never microphone evidence."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
output = ROOT/'evidence/synthetic_speech'
output.mkdir(parents=True, exist_ok=True)
commands = ['Đi đến khu vực A.', 'Di chuyển từ khu vực A đến khu vực B.',
            'Đi đến phòng thí nghiệm.', 'Đi đến khu vực D.',
            'Đi từ phòng A qua hành lang C rồi đến phòng B.',
            'Đi từ phòng học qua hành lang rồi đến phòng thí nghiệm.']
manifest_file = output/'manifest.json'
previous = {e['file']:e['text'] for e in json.loads(manifest_file.read_text())} if manifest_file.exists() else {}
manifest = []
downloaded = 0
for i, text in enumerate(commands, 1):
    target = output/f'command_{i}.mp3'
    if not (target.exists() and target.stat().st_size >= 100 and previous.get(str(target.relative_to(ROOT))) == text):
        url = 'https://translate.google.com/translate_tts?'+urlencode({'ie':'UTF-8', 'tl':'vi', 'client':'tw-ob', 'q':text})
        request = Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urlopen(request, timeout=30) as response:
            audio = response.read()
        if len(audio) < 100:
            raise RuntimeError('TTS không trả về audio')
        target.write_bytes(audio)
        downloaded += 1
    manifest.append({'file': str(target.relative_to(ROOT)), 'text': text, 'source': 'Google Translate TTS; synthetic Vietnamese speech'})
manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
print(f'Saved {len(commands)} synthetic speech fixtures ({downloaded} downloaded)')
