import { useState, useRef,useEffect } from 'react'
import tunerImg from './assets/tuner.png'

const API = import.meta.env.DEV ? 'http://localhost:8000' : ""

//drone tuning: predictions arrive every ~32ms, so 2 matching frames (~60ms) is enough to follow quick passages
const STABLE_FRAMES = 2
const RELEASE_MS = 250   //keep ringing through short gaps between notes, then fade out
const DRONE_VOLUME = 0.15
const GLIDE = 0.01       //setTargetAtTime time constants (s): pitch reaches the new note in ~30ms
const FADE = 0.03

export default function App() {
  const [isOn, setIsOn]  = useState(false)
  const [soundOn, setSoundOn] = useState(true)
  const audioCtxRef = useRef(null)
  const streamRef = useRef(null)
  const audioNode = useRef(null)
  const [error, setError] = useState(null)
  const audio = {
    audio: {
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    }
  }
  const inFlightRef = useRef(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!isOn) {
      return
    }
    //use effect
    let cancelled = false
    const start = async() => {
      try{
        audioCtxRef.current = new AudioContext({sampleRate: 16000})
        await audioCtxRef.current.audioWorklet.addModule('/pcm-processor.js')
        if (cancelled) {audioCtxRef.current.close(); return}
  
        streamRef.current = await navigator.mediaDevices.getUserMedia(audio)
        if (cancelled) {streamRef.current.getTracks().forEach(t=>t.stop()); audioCtxRef.current.close();return}
        
        audioNode.current = new AudioWorkletNode(audioCtxRef.current, 'pcm-processor')
        audioNode.current.port.onmessage = async (e) => {
        
          if (inFlightRef.current) return
          inFlightRef.current = true
          try{
            const res = await fetch(`${API}/predict?sr=16000`, {
              method: 'POST',
              body: e.data.buffer,
            })
            if (!res.ok) return
            setResult(await res.json())
          } catch{

          } finally {
            inFlightRef.current = false
          }
        }
        
        audioCtxRef.current.createMediaStreamSource(streamRef.current).connect(audioNode.current)
      } catch (err) {
        setError('Mic access denied')
        setIsOn(false)
      }
    }

    start()
    //turn off
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach(t=>t.stop())
      audioCtxRef.current?.close()
      streamRef.current = null
      audioCtxRef.current = null
      inFlightRef.current = false
      setResult(null)
    }
    
  }, [isOn])

  useDrone(isOn && soundOn, result)

  return (
    <main className="page">
      <HeadphoneNotice />

      <div className="tuner-card">
        <TunerImage />
        <Heading />
        <NoteDisplay isOn={isOn} result={result} />
        {error && <ErrorMessage message={error} />}
        <TuneButton isOn={isOn} onToggle={() => { setError(null); setIsOn(prev => !prev) }} />
        <SoundToggle soundOn={soundOn} onToggle={() => setSoundOn(prev => !prev)} />
      </div>
    </main>
  )
}

//librosa sends notes like "A♯4" -> split into letter, sharp/flat, octave so each can be styled
function splitNote(note){
  const m = note.match(/^([A-G])([♯#♭b]?)(-?\d+)$/)
  return m ? { letter: m[1], accidental: m[2], octave: m[3] } : { letter: note, accidental: '', octave: '' }
}

//same formula as midi_to_Hz in app/features.py
function midiToHz(midi){
  return 440 * 2 ** ((midi - 69) / 12)
}

//reference tone that follows the detected note
//without headphones the mic hears the drone and the tuner can lock onto its own output
function useDrone(active, result){
  const ctxRef = useRef(null)
  const oscRef = useRef(null)
  const gainRef = useRef(null)
  const soundingRef = useRef(false)
  const candidateRef = useRef({ midi: null, count: 0 })
  const releaseRef = useRef(null)

  //own context at the default rate: the 16kHz capture context would cut off high notes and overtones
  useEffect(() => {
    if (!active) return
    const ctx = new AudioContext()
    ctx.resume()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle' //softer than square, easier to hear than a pure sine on small speakers
    gain.gain.value = 0
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    ctxRef.current = ctx
    oscRef.current = osc
    gainRef.current = gain

    return () => {
      clearTimeout(releaseRef.current)
      ctx.close()
      ctxRef.current = null
      oscRef.current = null
      gainRef.current = null
      soundingRef.current = false
      candidateRef.current = { midi: null, count: 0 }
    }
  }, [active])

  useEffect(() => {
    const ctx = ctxRef.current
    if (!ctx) return

    const top = result?.predictions?.[0]
    const candidate = candidateRef.current
    if (!top || result.low_confidence) {
      //silence/unsure: don't cut the drone here, the release timer fades it if this lasts
      candidate.midi = null
      candidate.count = 0
      return
    }
    candidate.count = candidate.midi === top.midi ? candidate.count + 1 : 1
    candidate.midi = top.midi
    if (candidate.count < STABLE_FRAMES) return

    const now = ctx.currentTime
    const hz = midiToHz(top.midi)
    if (soundingRef.current) {
      oscRef.current.frequency.setTargetAtTime(hz, now, GLIDE)
    } else {
      //coming back from silence: jump straight to the note instead of sliding up from the last one
      oscRef.current.frequency.cancelScheduledValues(now)
      oscRef.current.frequency.setValueAtTime(hz, now)
    }
    gainRef.current.gain.setTargetAtTime(DRONE_VOLUME, now, FADE)
    soundingRef.current = true

    clearTimeout(releaseRef.current)
    releaseRef.current = setTimeout(() => {
      if (!ctxRef.current) return
      gainRef.current.gain.setTargetAtTime(0, ctxRef.current.currentTime, FADE)
      soundingRef.current = false
    }, RELEASE_MS)
  }, [result])
}

function HeadphoneNotice() {
  return (
    <p className="headphone-notice"> Plug in headphones for feedback</p>
  )
}

function TunerImage() {
  return (
    <img src={tunerImg} className="tuner-img" width="120" height="120" alt="" />
  )
}

function Heading() {
  return (
    <header className="heading">
      <h1>Tuner</h1>
      <p className="subtitle">Play a single note and hold it steady</p>
    </header>
  )
}

//screen is always rendered so the page doesn't jump when tuning starts/stops
function NoteDisplay({ isOn, result }) {
  const top = result?.predictions?.[0]

  let body
  if (!isOn) {
    body = <span className="lcd-status">press start</span>
  } else if (!top) {
    body = <span className="lcd-status listening">listening<span className="dots" /></span>
  } else {
    const { letter, accidental, octave } = splitNote(top.note)
    const pct = Math.round(top.confidence * 100)
    body = (
      <>
        <div className={result.low_confidence ? 'lcd-note dim' : 'lcd-note'}>
          {letter}
          {accidental && <span className="lcd-accidental">{accidental}</span>}
          <span className="lcd-octave">{octave}</span>
        </div>
        <div className="confidence">
          <div className="confidence-bar"><div style={{ width: `${pct}%` }} /></div>
          <span>{result.low_confidence ? 'low confidence' : `${pct}%`}</span>
        </div>
      </>
    )
  }

  return <div className="lcd" aria-live="polite">{body}</div>
}

function ErrorMessage({ message }) {
  return <p className="error" role="alert">{message}</p>
}

function TuneButton({ isOn, onToggle }) {
  return (
    <button
      type="button"
      className={isOn ? 'switch switch-on' : 'switch'}
      onClick={onToggle}
      >
      {isOn ? 'Stop Tuning' : 'Start Tuning'}
    </button>
  )
}

function SoundToggle({ soundOn, onToggle }) {
  return (
    <button
      type="button"
      className="sound-toggle"
      aria-pressed={soundOn}
      onClick={onToggle}
      >
      {soundOn ? 'Reference tone: on' : 'Reference tone: off'}
    </button>
  )
}

function useHeadphoneCheck(active){
  const [headphoneConnected, setHeadphoneConnected] = useState(null)
  useEffect(() => {
    if(!active){
      setHeadphoneConnected(null)
      return;
    }

    let cancelled = false
    const checkHeadphone = async () => {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const hasHeadphone = devices.some(device => device.label.toLowerCase().includes('headphone') ||
                                                  device.label.toLowerCase().includes('headset') ||
                                                  device.label.toLowerCase().includes('earphone') ||
                                                  device.label.toLowerCase().includes('airpod'));
      if(!cancelled){
        setHeadphoneConnected(hasHeadphone);
      }
    }
    checkHeadphone()
    navigator.mediaDevices.addEventListener('devicechange', checkHeadphone)
    return () => {
      cancelled = true
      navigator.mediaDevices.removeEventListener('devicechange', checkHeadphone)
    }
  }, [active])
  return headphoneConnected
}

// import { useState, useEffect } from 'react'

// export function useHeadphoneCheck(active) {
//   const [isHeadphoneConnected, setIsHeadphoneConnected] = useState(null)

//   useEffect(() => {
//     if (!active) { setIsHeadphoneConnected(null); return }
//     let cancelled = false

//     const checkDevices = async () => {
//       try {
//         const devices = await navigator.mediaDevices.enumerateDevices()
//         const hasHeadphones = devices
//           .filter(d => d.kind === 'audiooutput')
//           .some(d => {
//             const label = d.label.toLowerCase()
//             return label.includes('headphone') ||
//                    label.includes('headset') ||
//                    label.includes('earphone') ||
//                    label.includes('airpod')
//           })
//         if (!cancelled) setIsHeadphoneConnected(hasHeadphones)
//       } catch (error) {
//         console.error("Error reading devices:", error)
//       }
//     }

//     checkDevices()
//     navigator.mediaDevices.addEventListener('devicechange', checkDevices)
//     return () => {
//       cancelled = true
//       navigator.mediaDevices.removeEventListener('devicechange', checkDevices)
//     }
//   }, [active])

//   return isHeadphoneConnected
// }
