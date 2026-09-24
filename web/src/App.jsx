import { useState, useRef,useEffect } from 'react'
import tunerImg from './assets/tuner.png'

const API = import.meta.env.DEV ? 'http://localhost:8000' : ""

export default function App() {
  const [isOn, setIsOn]  = useState(false)
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

  return (
    <main className="page">
      <HeadphoneNotice />

      <div className="tuner-card">
        <TunerImage />
        <Heading />
        <NoteDisplay isOn={isOn} result={result} />
        {error && <ErrorMessage message={error} />}
        <TuneButton isOn={isOn} onToggle={() => { setError(null); setIsOn(prev => !prev) }} />
      </div>
    </main>
  )
}

//librosa sends notes like "A♯4" -> split into letter, sharp/flat, octave so each can be styled
function splitNote(note){
  const m = note.match(/^([A-G])([♯#♭b]?)(-?\d+)$/)
  return m ? { letter: m[1], accidental: m[2], octave: m[3] } : { letter: note, accidental: '', octave: '' }
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

//play audio as well
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
