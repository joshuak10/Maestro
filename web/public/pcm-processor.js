#console.log('worklet file loaded')

//load class
class PcmProcessor extends AudioWorkletProcessor {
    constructor(){
        super();
        this._buffer = new Float32Array(8000)
        this._count = 0
    }

    process(inputs){
        const audio = inputs[0]?.[0]
        if (!audio) return true //checks first audio bin for silence

        for (let i = 0; i < audio.length; i++){
            this._buffer[this._count] = audio[i]
            this._count ++
            if (this._count == 8000){
                this.port.postMessage(this._buffer.slice())
                this._count = 0
            }
        }
        return true
    }
}
registerProcessor('pcm-processor', PcmProcessor)