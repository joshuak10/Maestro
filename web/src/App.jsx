import { useState, useRef,useEffect } from 'react'
import tunerImg from './assets/tuner.png'

function display(result){
  if (!result || result.predictions.length === 0) return "listening..."
  if (result.low_confidence) return 'low confidence'
  return result.predictions[0].note
}

const API = import.meta.env.DEV ? 'http://localhost:8000' : ""

function App() {
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
      <div className = "center-container">
        <div className="hero">
          <img src={tunerImg} className="base" width="170" height="180" alt="" />
        </div>
        <div>
          <h1>Click the Button below to Tune!</h1>
        </div>
        {isOn && <p>{display(result)}</p>}
        {error && <p className="error">{error}</p>}
        <button
          type="button"
          className={isOn ? 'switch switch-on' : 'switch'}
          onClick={() => setIsOn(prev => !prev)}
          >
          {isOn ? 'Stop Tuning' : 'Start Tuning'}
        </button>
      </div>
    </section>
  )
}

export default App
