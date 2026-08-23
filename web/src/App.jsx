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
    <section id="center">
      <HeadphoneNotice />

      <div className = "center-container">
        <TunerImage />
        <Heading />
        {isOn && <NoteDisplay result={result} />}
        {error && <ErrorMessage message={error} />}
        <TuneButton isOn={isOn} onToggle={() => setIsOn(prev => !prev)} />
      </div>
    </section>
  )
}

const font = { fontFamily : '"Gill Sans", sans-serif' }

function display(result){
  if (!result || result.predictions.length === 0) return "listening..."
  if (result.low_confidence) return 'low confidence'
  return result.predictions[0].note
}

function HeadphoneNotice() {
  return (
    <div className = 'headphone-text'>
      <p > Plug in Headphones for feedback!</p>
    </div>
  )
}

function TunerImage() {
  return (
    <div className="hero">
      <img src={tunerImg} className="base" width="170" height="180" alt="" />
    </div>
  )
}

function Heading() {
  return (
    <div>
      <h1>Click the Button below to Tune!</h1>
    </div>
  )
}

function NoteDisplay({ result }) {
  return <p style={font}>{display(result)}</p>
}

function ErrorMessage({ message }) {
  return <p className="error">{message}</p>
}

function TuneButton({ isOn, onToggle }) {
  return (
    <button
      type="button"
      className={isOn ? 'switch switch-on' : 'switch'}
      style={font}
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
