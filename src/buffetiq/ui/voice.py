"""Hold-to-talk button shared by the runner phone and the kitchen board.

Press and hold to record with the browser's microphone; let go to send. The
recording is uploaded to the app and the component's `submit` event fires with
the file path. If the browser cannot record (no microphone, permission refused,
or a plain http link on a phone, where browsers block the microphone), the
event fires with "ERROR:<reason>" so the page can offer typing instead.
"""

from __future__ import annotations

import gradio as gr

from buffetiq.style import ICONS

HOLD_JS = """
let rec = null, chunks = [], stream = null, started = 0;
const btn = element.querySelector('button');
const label = btn.querySelector('.lbl');
const idle = label ? label.textContent : '';
const setState = (s, text) => { btn.dataset.state = s; if (label) label.textContent = text; };
const send = (value) => { props.value = value; trigger('submit'); };
const start = async (e) => {
  e.preventDefault();
  if (rec && rec.state === 'recording') return;
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { send('ERROR:SecurityError'); return; }
    stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true}});   // the browser filters steady room noise and levels the voice
    rec = new MediaRecorder(stream); chunks = []; started = Date.now();
    rec.ondataavailable = ev => { if (ev.data.size) chunks.push(ev.data); };
    rec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      if (Date.now() - started < 400 || !chunks.length) { setState('', idle); send('ERROR:TooShort'); return; }
      setState('thinking', 'Thinking');
      const type = rec.mimeType || 'audio/webm';
      const ext = type.includes('mp4') ? 'mp4' : (type.includes('ogg') ? 'ogg' : 'webm');
      try {
        const res = await upload(new File([new Blob(chunks, {type})], 'question.' + ext, {type}));
        send(res.path);
      } catch (err) { setState('', idle); send('ERROR:UploadFailed'); }
    };
    rec.start(); setState('recording', 'Listening');
  } catch (err) { setState('', idle); send('ERROR:' + (err && err.name ? err.name : 'Unknown')); }
};
const stop = () => { if (rec && rec.state === 'recording') rec.stop(); };
btn.addEventListener('pointerdown', start);
btn.addEventListener('pointerup', stop);
btn.addEventListener('pointerleave', stop);
btn.addEventListener('pointercancel', stop);
btn.addEventListener('contextmenu', e => e.preventDefault());
btn.addEventListener('keydown', e => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) start(e); });
btn.addEventListener('keyup', e => { if (e.key === ' ' || e.key === 'Enter') stop(); });
"""


def _mic_svg(size: int) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS["mic"]}</svg>')


def hold_button(label: str, aria: str, kind: str, elem_id: str) -> gr.HTML:
    """kind: 'phone' (132 px round, screen 02) or 'board' (96 px strip button, screen 01)."""
    size = 32 if kind == "phone" else 30
    template = (f'<button type="button" class="bq-hold bq-hold-{kind}" aria-label="{aria}">'
                f'{_mic_svg(size)}<span class="lbl">{label}</span></button>')
    return gr.HTML(value="", html_template=template, js_on_load=HOLD_JS, elem_id=elem_id,
                   elem_classes=["bq-hold-wrap", f"bq-hold-wrap-{kind}"])
