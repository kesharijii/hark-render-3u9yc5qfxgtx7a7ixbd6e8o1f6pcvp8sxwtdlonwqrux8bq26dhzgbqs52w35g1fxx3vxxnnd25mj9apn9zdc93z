import asyncio, json, sys, edge_tts
# usage: python tts.py script.txt [voice] [rate]
txt=open(sys.argv[1]).read().replace('\n',' ')
VOICE=sys.argv[2] if len(sys.argv)>2 else 'en-US-AndrewMultilingualNeural'
RATE=sys.argv[3] if len(sys.argv)>3 else '-5%'
async def main():
    c=edge_tts.Communicate(txt,VOICE,rate=RATE,boundary="WordBoundary")
    words=[]
    with open('voice.mp3','wb') as f:
        async for ch in c.stream():
            if ch['type']=='audio': f.write(ch['data'])
            elif ch['type']=='WordBoundary':
                words.append(dict(w=ch['text'],t=ch['offset']/1e7,d=ch['duration']/1e7))
    json.dump(words,open('words.json','w'),indent=0)
asyncio.run(main())
