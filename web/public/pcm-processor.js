console.log('worklet file loaded')

const WINDOW = 2048
const HOP = 512  

//load class
class PcmProcessor extends AudioWorkletProcessor { //must extend audioworkletprocessor
    constructor(){
        super();
        this._buffer = new Float32Array(WINDOW) //ring buffer, always holds the latest 0.5s
        this._write = 0     //next index to overwrite (= oldest sample once full)
        this._filled = 0    //don't send until the first full window
        this._sinceSend = 0
    }

    process(inputs){
        const audio = inputs[0]?.[0]
        if (!audio) return true //checks first audio bin for silence

        for (let i = 0; i < audio.length; i++){
            this._buffer[this._write] = audio[i]
            this._write = (this._write + 1) % WINDOW
            if (this._filled < WINDOW) this._filled++
            this._sinceSend++

            if (this._filled === WINDOW && this._sinceSend >= HOP){
                const out = new Float32Array(WINDOW)
                out.set(this._buffer.subarray(this._write))
                out.set(this._buffer.subarray(0, this._write), WINDOW - this._write)
                this.port.postMessage(out, [out.buffer])
                this._sinceSend = 0
            }
        }
        return true
    }
}
registerProcessor('pcm-processor', PcmProcessor)
