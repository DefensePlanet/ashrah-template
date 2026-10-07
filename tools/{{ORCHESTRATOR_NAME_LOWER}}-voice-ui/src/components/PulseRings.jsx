import React, { useMemo } from 'react'

/**
 * PulseRings - Expanding concentric rings effect inspired by BuilderOS TalkOrbOverlay
 * Creates the retro crypto punk neon aesthetic with pulsing circles
 */
export default function PulseRings({ color = '#00D9FF', active = false, audioLevel = 0 }) {
  // Generate multiple ring configurations
  const rings = useMemo(() => [
    { scale: 1.15, duration: 2.5, delay: 0, opacity: 0.4 },
    { scale: 1.45, duration: 3.0, delay: 0.5, opacity: 0.25 },
    { scale: 1.8, duration: 3.5, delay: 1.0, opacity: 0.15 },
  ], [])

  const baseSize = 'min(60vw, 60vh)'

  return (
    <div style={{
      position: 'absolute',
      width: baseSize,
      height: baseSize,
      left: '50%',
      top: '50%',
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
      zIndex: 5
    }}>
      {/* Static glow ring - calm glow, intensifies with audio */}
      <div style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}00 40%, ${color}${audioLevel > 0.05 ? '25' : '15'} 55%, ${color}00 70%)`,
        transition: 'background 0.5s ease, filter 0.3s ease',
        filter: `blur(${10 + audioLevel * 15}px)`,
      }} />

      {/* Animated pulse rings - smooth fade based on audio level */}
      {rings.map((ring, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            left: '50%',
            top: '50%',
            borderRadius: '50%',
            border: `2px solid ${color}`,
            // Smooth opacity based on audio level - no hard threshold
            opacity: ring.opacity * (0.1 + audioLevel * 1.2),
            // Animate when there's audio
            animation: audioLevel > 0.02
              ? `pulse-ring ${ring.duration}s ease-out ${ring.delay}s infinite`
              : 'none',
            transform: 'translate(-50%, -50%)',
            boxShadow: `0 0 ${8 + audioLevel * 15}px ${color}${Math.round(audioLevel * 60).toString(16).padStart(2, '0')}`,
            transition: 'opacity 0.6s ease-out, box-shadow 0.4s ease-out'
          }}
        />
      ))}

      {/* Inner glow core - calm base, intensifies with audio */}
      <div style={{
        position: 'absolute',
        width: '80%',
        height: '80%',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}${Math.round(10 + audioLevel * 12).toString(16).padStart(2, '0')} 0%, ${color}00 60%)`,
        filter: `blur(${20 + audioLevel * 15}px)`,
        transition: 'background 0.6s ease-out, filter 0.4s ease-out'
      }} />

      {/* Audio-reactive burst ring - smooth fade based on level */}
      <div style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        left: '50%',
        top: '50%',
        transform: `translate(-50%, -50%) scale(${1 + audioLevel * 0.15})`,
        borderRadius: '50%',
        border: `1px solid ${color}`,
        opacity: audioLevel * 0.4,
        boxShadow: `0 0 ${15 * audioLevel}px ${color}`,
        transition: 'transform 0.25s ease-out, opacity 0.3s ease-out, box-shadow 0.3s ease-out'
      }} />
    </div>
  )
}
