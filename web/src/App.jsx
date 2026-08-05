import { useState } from 'react'

import tunerImg from './assets/tuner.png'

function App() {
  const [count, setCount] = useState(0)

  return (
    <section id="center">
      <div className = "center-container">
        <div className="hero">
          <img src={tunerImg} className="base" width="170" height="180" alt="" />
        </div>
        <div>
          <h1>Click the Button below to Tune!</h1>
        </div>
        <button
          type="button"
          className="counter"
          onClick={() => setCount((count) => count + 1)}
          >
          Tuning Off
        </button>
      </div>
    </section>
  )
}

export default App
