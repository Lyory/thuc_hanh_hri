"""Describe ALSA inputs and prefer a USB/digital microphone over a headset jack."""
from pathlib import Path
import re


def inputs():
    import sounddevice as sd
    descriptors={}
    pcm=Path('/proc/asound/pcm')
    if pcm.exists():
        for line in pcm.read_text().splitlines():
            m=re.match(r'(\d+)-(\d+):\s*(.*?)\s*:',line)
            if m:
                descriptors[(int(m[1]),int(m[2]))]=m[3]
    result=[]
    for i,d in enumerate(sd.query_devices()):
        if d['max_input_channels']<=0:
            continue
        match=re.search(r'hw:(\d+),(\d+)',d['name'])
        detail=descriptors.get((int(match[1]),int(match[2])),'') if match else ''
        result.append((i,d['name']+(f' — {detail}' if detail else '')))
    return result


def default_input():
    choices=inputs()
    for word in ('usb','dmic'):
        for i,name in choices:
            if word in name.lower():
                return i
    return None
