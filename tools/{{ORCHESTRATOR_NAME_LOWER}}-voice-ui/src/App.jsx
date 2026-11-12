import React, { useState, useEffect } from 'react'
import ReactBitsOrb from './components/ReactBitsOrb'
import PulseRings from './components/PulseRings'
import AudioProcessor from './components/AudioProcessor'

// BuilderOS Terminal Color Palette
const COLORS = {
  background: '#0a0e1a',
  cyan: '#00D9FF',    // AI speaking
  pink: '#FF6B9D',    // User speaking
}

// Who's speaking determines the color
// 'idle' = no one (cyan, calm)
// 'user' = user is speaking (pink, animated)
// 'ai' = AI is responding (cyan, animated)

export default function App() {
  const [userAudioLevel, setUserAudioLevel] = useState(0)
  const [aiAudioLevel, setAiAudioLevel] = useState(0)
  const [isAiSpeaking, setIsAiSpeaking] = useState(false)

  // Always listening - mic active on mount
  const [micActive] = useState(true)

  // Simulate AI speaking (for demo - in production this would be triggered externally)
  useEffect(() => {
    // Demo: Press 'space' to simulate AI speaking
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && !e.repeat) {
        e.preventDefault()
        setIsAiSpeaking(true)
      }
    }
    const handleKeyUp = (e) => {
      if (e.code === 'Space') {
        setIsAiSpeaking(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [])

  // Simulate AI audio level when "speaking"
  useEffect(() => {
    if (isAiSpeaking) {
      const interval = setInterval(() => {
        const t = Date.now() / 1000
        const level =
          0.3 +
          0.25 * Math.sin(t * 4.5) +
          0.15 * Math.sin(t * 7.2) +
          0.1 * Math.sin(t * 11.3) +
          0.1 * Math.random()
        setAiAudioLevel(Math.max(0, Math.min(1, level)))
      }, 50)
      return () => {
        clearInterval(interval)
        setAiAudioLevel(0)
      }
    } else {
      setAiAudioLevel(0)
    }
  }, [isAiSpeaking])

  // Determine who's speaking and the effective audio level
  const isUserSpeaking = userAudioLevel > 0.02
  const speaker = isAiSpeaking ? 'ai' : isUserSpeaking ? 'user' : 'idle'
  const effectiveAudioLevel = isAiSpeaking ? aiAudioLevel : userAudioLevel

  // Color based on who's speaking
  const currentColor = speaker === 'user' ? COLORS.pink : COLORS.cyan

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: COLORS.background,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* Subtle scanline overlay for retro effect */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)',
        pointerEvents: 'none',
        zIndex: 100
      }} />

      {/* Pulsing rings behind the orb */}
      <PulseRings
        color={currentColor}
        active={effectiveAudioLevel > 0.02}
        audioLevel={effectiveAudioLevel}
      />

      {/* React Bits Orb */}
      <div style={{
        width: 'min(70vw, 70vh)',
        height: 'min(70vw, 70vh)',
        position: 'relative',
        zIndex: 10,
        filter: `drop-shadow(0 0 ${20 + effectiveAudioLevel * 20}px ${currentColor}66)`,
        transition: 'filter 0.3s ease-out'
      }}>
        <ReactBitsOrb
          state={speaker}
          audioLevel={effectiveAudioLevel}
          hoverIntensity={0.3}
          rotateOnHover={true}
          forceHoverState={effectiveAudioLevel > 0.02}
          backgroundColor={COLORS.background}
        />
      </div>

      {/* Always listening - AudioProcessor always active */}
      {micActive && (
        <AudioProcessor onAudioLevel={setUserAudioLevel} />
      )}

      {/* Header */}
      <div style={{
        position: 'fixed',
        top: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        color: COLORS.cyan,
        fontSize: 11,
        letterSpacing: '0.3em',
        textTransform: 'uppercase',
        fontWeight: 500,
        fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
        textShadow: `0 0 10px ${COLORS.cyan}66`,
        opacity: 0.8
      }}>
        {{ORCHESTRATOR_NAME_UPPER}} // VOICE INTERFACE
      </div>

      {/* Status indicator - subtle, bottom of screen */}
      <div style={{
        position: 'fixed',
        bottom: 40,
        left: '50%',
        transform: 'translateX(-50%)',
        padding: '6px 16px',
        background: `${currentColor}10`,
        border: `1px solid ${currentColor}30`,
        borderRadius: 16,
        color: currentColor,
        fontSize: 9,
        letterSpacing: '0.2em',
        textTransform: 'uppercase',
        fontWeight: 500,
        fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
        opacity: speaker === 'idle' ? 0.4 : 0.8,
        transition: 'all 0.4s ease'
      }}>
        {speaker === 'idle' && 'Listening'}
        {speaker === 'user' && 'You'}
        {speaker === 'ai' && '{{ORCHESTRATOR_NAME}}'}
      </div>

      {/* Demo hint */}
      <div style={{
        position: 'fixed',
        bottom: 12,
        left: '50%',
        transform: 'translateX(-50%)',
        color: COLORS.cyan,
        fontSize: 8,
        letterSpacing: '0.15em',
        textTransform: 'uppercase',
        fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
        opacity: 0.3
      }}>
        Hold SPACE to simulate AI response
      </div>
    </div>
  )
}
