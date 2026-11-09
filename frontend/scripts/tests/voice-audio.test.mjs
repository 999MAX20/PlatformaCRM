import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import test from "node:test";
const source=fs.readFileSync(new URL("../../src/features/voice/audio.ts",import.meta.url),"utf8");
const encodeWave=vm.runInNewContext(stripTypeScriptTypes(source).replace("export ","")+"\nencodeWave",{Blob});

function worklet() {
  let Processor; const messages=[];
  class BaseProcessor { constructor(){this.port={postMessage:data=>messages.push(data),onmessage:null};} }
  const context={AudioWorkletProcessor:BaseProcessor,Float32Array,currentFrame:0,registerProcessor:(_,value)=>{Processor=value;}};
  vm.runInNewContext(fs.readFileSync(new URL('../../src/features/voice/pcm-worklet.js',import.meta.url),'utf8'),context);
  const processor=new Processor();
  return {messages,processor,context,feed(samples){processor.process([[samples]]);context.currentFrame+=samples.length;}};
}
test("finishing capture flushes the partial buffer before acknowledgement and ignores later audio",()=>{
  const w=worklet();w.feed(new Float32Array([.1,.2]));w.feed(new Float32Array([.3,.4]));
  assert.equal(w.messages.length,0);
  w.processor.port.onmessage({data:{type:'finish'}});w.feed(new Float32Array([.9]));
  assert.equal(w.messages.length,2);assert.equal(w.messages[0].offset,0);
  assert.deepEqual([...w.messages[0].samples],[...new Float32Array([.1,.2,.3,.4])]);
  assert.equal(w.messages[1].type,'finished');assert.equal(w.messages[1].frames,4);
});
test("long PCM capture preserves start middle end and silence across buffer boundaries",async()=>{
  const w=worklet();const expected=new Float32Array(48000*18);
  for(let i=0;i<expected.length;i++)expected[i]=i>=48000*8&&i<48000*9?0:Math.sin(i/17)*(i<48000*6?.2:i<48000*12?.5:.8);
  for(let i=0;i<expected.length;i+=128)w.feed(expected.slice(i,i+128));
  w.processor.port.onmessage({data:{type:'finish'}});
  let offset=0;const chunks=[];
  for(const message of w.messages.filter(m=>m.type==='chunk')){
    assert.equal(message.offset,offset);assert.deepEqual(message.samples,expected.slice(offset,offset+message.samples.length));
    chunks.push(message.samples);offset+=message.samples.length;
  }
  assert.equal(offset,expected.length);
  const encoded=Buffer.from(await encodeWave(chunks,48000).arrayBuffer());
  assert.equal(encoded.length,44+16000*18*2);
  for(const second of [1,6,10,16]){
    let energy=0;for(let i=second*16000;i<(second+1)*16000;i++)energy+=encoded.readInt16LE(44+i*2)**2;
    assert.ok(energy>1e10,`speech energy missing at ${second}s`);
  }
  assert.equal(encoded.readInt16LE(44+16000*8*2),0);
});
test("a skipped render block or lost input reports interruption instead of silently splicing audio",()=>{
  for(const kind of ['gap','input']){
    const w=worklet();w.feed(new Float32Array(128).fill(.5));
    if(kind==='gap'){w.context.currentFrame+=128;w.feed(new Float32Array(128).fill(.5));}
    else w.processor.process([[]]);
    assert.equal(w.messages.at(-1).type,'interrupted');
    const count=w.messages.length;w.feed(new Float32Array(128));assert.equal(w.messages.length,count);
  }
});
test("voice WAV is mono PCM16 at 16 kHz with correct duration and clipping",async()=>{
  const wave=encodeWave([new Float32Array(48000).fill(2)],48000);
  const bytes=Buffer.from(await wave.arrayBuffer());
  assert.equal(bytes.toString('ascii',0,4),'RIFF');assert.equal(bytes.toString('ascii',8,12),'WAVE');
  assert.equal(bytes.readUInt16LE(22),1);assert.equal(bytes.readUInt32LE(24),16000);assert.equal(bytes.readUInt16LE(34),16);
  assert.equal(bytes.length,32044);assert.equal(bytes.readInt16LE(44),32767);
});
test("chunk boundaries preserve negative samples and recording is bounded to sixty seconds",async()=>{
  const wave=encodeWave([new Float32Array(16000).fill(-2),new Float32Array(16000*60).fill(.5)],16000);
  const bytes=Buffer.from(await wave.arrayBuffer());assert.equal(bytes.length,1920044);
  assert.equal(bytes.readInt16LE(44),-32768);assert.equal(bytes.readInt16LE(32044),16384);
});
test("empty capture stays empty instead of inventing speech",async()=>{
  const bytes=Buffer.from(await encodeWave([],16000).arrayBuffer());assert.equal(bytes.length,44);assert.equal(bytes.readUInt32LE(40),0);
});
const contextSource=fs.readFileSync(new URL("../../src/features/voice/context.ts",import.meta.url),"utf8");
const voiceCardContext=vm.runInNewContext(stripTypeScriptTypes(contextSource).replaceAll("export ","")+"\nvoiceCardContext",{URLSearchParams});
test("voice context selects the actual card, never a client filter on appointments",()=>{
  assert.equal(voiceCardContext('/app/appointments','?client=42'),undefined);
  assert.equal(JSON.stringify(voiceCardContext('/app/appointments','?client=42&appointment=9')),JSON.stringify({entity:'appointments',id:9}));
  assert.equal(JSON.stringify(voiceCardContext('/app/clients/42','')),JSON.stringify({entity:'clients',id:42}));
  assert.equal(voiceCardContext('/app/clients','?client=-1'),undefined);
});
