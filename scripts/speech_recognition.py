"""Vietnamese Whisper ASR with visible capture diagnostics; no extra model needed."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from audio_devices import inputs, default_input

ROOT=Path(__file__).resolve().parents[1]


def resample(audio,rate):
    if rate==16000:
        return audio
    import av
    frame=av.AudioFrame.from_ndarray(audio.reshape(1,-1),format='flt',layout='mono')
    frame.sample_rate=rate
    converter=av.AudioResampler(format='fltp',layout='mono',rate=16000)
    frames=converter.resample(frame)+converter.resample(None)
    return np.concatenate([f.to_ndarray().reshape(-1) for f in frames]).astype(np.float32)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--audio',nargs='+',help='WAV/MP3; mỗi file là một câu lệnh')
    p.add_argument('--model',default='small')
    p.add_argument('--cpu-threads',type=int,default=2)
    p.add_argument('--seconds',type=float,default=6.)
    p.add_argument('--device',type=int)
    p.add_argument('--once',action='store_true',help='Thu một câu ngay sau khi nạp model; dùng cho giao diện')
    p.add_argument('--list-devices',action='store_true')
    p.add_argument('--download-only',action='store_true')
    p.add_argument('--no-publish',action='store_true',help='Không gửi lệnh điều hướng')
    a=p.parse_args()
    if a.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        print('Đầu vào:', inputs())
        print('Tự chọn:', default_input())
        return 0
    if not 0<a.seconds<=30 or a.cpu_threads<1:
        p.error('Thời gian thu phải trong (0,30], số luồng CPU phải dương')
    from faster_whisper import WhisperModel
    if a.download_only:
        WhisperModel(a.model,device='cpu',compute_type='int8',cpu_threads=a.cpu_threads,
                     download_root=str(ROOT/'models'))
        return 0
    rclpy.init()
    node=Node('speech_recognition')
    pub=node.create_publisher(String,'/voice_command',10)
    status=node.create_publisher(String,'/speech_recognition/status',10)
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and pub.get_subscription_count()==0:
        rclpy.spin_once(node,timeout_sec=.1)

    def report(state,message,**details):
        event={'time':time.time(),'state':state,'message':message,**details}
        status.publish(String(data=json.dumps(event,ensure_ascii=False)))
        print(json.dumps(event,ensure_ascii=False),flush=True)
        rclpy.spin_once(node,timeout_sec=.01)

    def transcribe(audio,source,**metrics):
        report('TRANSCRIBING','Đang chuyển giọng nói thành văn bản…',**metrics)
        segments,info=model.transcribe(audio,language='vi',beam_size=5,vad_filter=True,
            vad_parameters={'threshold':.35,'min_speech_duration_ms':150,'min_silence_duration_ms':250},
            condition_on_previous_text=False)
        # Whisper already applies its no-speech checks. A second independent
        # probability filter used to discard valid short Vietnamese commands.
        text=' '.join(s.text.strip() for s in segments).strip()
        event={'time':time.time(),'source':source,'text':text,'language':info.language,**metrics}
        log=ROOT/'evidence/transcripts.jsonl'
        log.parent.mkdir(exist_ok=True)
        with log.open('a') as stream:
            stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        if not text:
            report('EMPTY','Chưa nhận được tiếng nói. Chọn đúng micro, kiểm tra mute và thử nói gần hơn.',text='',**metrics)
            return
        report('RECOGNIZED','Đã nhận dạng: '+text,text=text,**metrics)
        if not a.no_publish:
            if pub.get_subscription_count()==0:
                report('NO_NAVIGATION','Đã nhận dạng nhưng chưa có node điều hướng; mở demo trước.',text=text)
            else:
                pub.publish(String(data=text))
                rclpy.spin_once(node,timeout_sec=.3)

    try:
        report('LOADING','Đang nạp model '+a.model+'…')
        model=WhisperModel(a.model,device='cpu',compute_type='int8',cpu_threads=a.cpu_threads,
                           download_root=str(ROOT/'models'))
        if a.audio:
            for filename in a.audio:
                transcribe(filename,filename)
        else:
            import sounddevice as sd
            if a.device is None:
                a.device=default_input()
            device=sd.query_devices(a.device,'input')
            rate=int(device['default_samplerate'])
            sd.check_input_settings(device=a.device,channels=1,samplerate=rate,dtype='float32')
            while True:
                if not a.once:
                    input('Enter để thu một câu; Ctrl+C để thoát. ')
                report('RECORDING',f'Đang thu {a.seconds:g} giây — nói ngay. Micro: {device["name"]}')
                audio=sd.rec(int(a.seconds*rate),samplerate=rate,channels=1,dtype='float32',device=a.device)
                sd.wait()
                audio=np.ascontiguousarray(audio[:,0])
                peak=float(np.max(np.abs(audio)))
                rms_db=20*math.log10(max(float(np.sqrt(np.mean(audio**2))),1e-9))
                metrics={'peak':round(peak,5),'rms_db':round(rms_db,1),'device':device['name']}
                if peak<.0005:
                    report('SILENT','Micro gần như không có tín hiệu. Kiểm tra mute hoặc chọn đầu vào khác.',text='',**metrics)
                else:
                    if peak<.1:
                        audio=audio*min(8.,.1/peak)
                    transcribe(resample(audio,rate),'microphone',**metrics)
                if a.once:
                    break
    except (KeyboardInterrupt,EOFError):
        return 0
    except Exception as error:
        report('ERROR',str(error))
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__=='__main__':
    sys.exit(main())
