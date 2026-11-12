import { useEffect, useRef } from 'react'

export default function AudioProcessor({ onAudioLevel }) {
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const streamRef = useRef(null)
  const animationFrameRef = useRef(null)

  useEffect(() => {
    let mounted = true

    async function initAudio() {
      try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        })

        if (!mounted) {
          stream.getTracks().forEach(track => track.stop())
          return
        }

        streamRef.current = stream

        // Create audio context
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        audioContextRef.current = audioContext

        // Create analyser node - high smoothing for fluid response
        const analyser = audioContext.createAnalyser()
        analyser.fftSize = 256
        analyser.smoothingTimeConstant = 0.85  // Higher = smoother (less jittery)
        analyserRef.current = analyser

        // Connect microphone to analyser
        const source = audioContext.createMediaStreamSource(stream)
        source.connect(analyser)

        // Start processing
        const dataArray = new Uint8Array(analyser.frequencyBinCount)
        let smoothedLevel = 0  // Internal smoothing

        function processAudio() {
          if (!mounted) return

          analyser.getByteFrequencyData(dataArray)

          // Calculate RMS (root mean square) for more accurate level
          let sum = 0
          for (let i = 0; i < dataArray.length; i++) {
            const normalized = dataArray[i] / 255
            sum += normalized * normalized
          }
          const rms = Math.sqrt(sum / dataArray.length)

          // Focus on voice frequencies (85-500 Hz)
          let voiceSum = 0
          const voiceStart = Math.floor(85 / (audioContext.sampleRate / analyser.fftSize))
          const voiceEnd = Math.floor(500 / (audioContext.sampleRate / analyser.fftSize))
          for (let i = voiceStart; i < Math.min(voiceEnd, dataArray.length); i++) {
            voiceSum += dataArray[i] / 255
          }
          const voiceLevel = voiceSum / (voiceEnd - voiceStart)

          // Combine RMS and voice-specific levels - reduced sensitivity
          const rawLevel = Math.min(1, (rms * 0.4 + voiceLevel * 0.6) * 1.5)

          // Apply internal smoothing - slower rise for smooth transition, slower fall for natural decay
          const smoothFactor = rawLevel > smoothedLevel ? 0.08 : 0.03
          smoothedLevel += (rawLevel - smoothedLevel) * smoothFactor

          // Soft noise gate - gradual fade near threshold instead of hard cutoff
          let level = smoothedLevel
          if (smoothedLevel < 0.15) {
            // Fade out smoothly below threshold
            level = smoothedLevel < 0.05 ? 0 : smoothedLevel * (smoothedLevel / 0.15)
          }

          onAudioLevel(level)

          animationFrameRef.current = requestAnimationFrame(processAudio)
        }

        processAudio()
      } catch (error) {
        console.error('Failed to access microphone:', error)
        // Silently fail - don't alert, just set level to 0 (silent mode)
        onAudioLevel(0)
      }
    }

    initAudio()

    // Cleanup
    return () => {
      mounted = false

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }

      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
      }
    }
  }, [onAudioLevel])

  return null
}
