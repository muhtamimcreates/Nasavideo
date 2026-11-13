import json,sys,soundfile as sf
from kokoro_onnx import Kokoro
k=Kokoro('kokoro.onnx','voices.bin')
voice=sys.argv[1]; out=sys.argv[2]
lines=json.load(open('/home/user/Nasavideo/video/script.json'))
import os; os.makedirs(out,exist_ok=True)
for i,l in enumerate(lines[:int(sys.argv[3]) if len(sys.argv)>3 else None]):
    s,sr=k.create(l.get('say',l['text']).replace('[','').replace(']',''),voice=voice,speed=float(__import__('os').environ.get('VO_SPEED','0.92')),lang='en-us')
    sf.write(f'{out}/{i:02d}.wav',s,sr); print(i,len(s)/sr)
