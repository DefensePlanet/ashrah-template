import React from 'react'

// Default BuilderOS terminal color palette
const DEFAULT_COLORS = {
  background: '#0a0e1a',
  cyan: '#00D9FF',
  pink: '#FF6B9D',
  purple: '#A78BFA',
  green: '#4ADE80',
  orange: '#FB923C',
}

const DEFAULT_STATE_COLORS = {
  idle: '#00D9FF',
  listening: '#00D9FF',
  speaking: '#A78BFA',
  thinking: '#FF6B9D',
}

export default function Controls({
  state,
  states,
  onStateChange,
  onAudioToggle,
  isAudioActive,
  audioLevel,
  colors = DEFAULT_COLORS,
  stateColors = DEFAULT_STATE_COLORS
}) {
  const currentColor = stateColors[state] || colors.cyan

  const styles = {
    container: {
      position: 'fixed',
      bottom: 32,
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 16,
      zIndex: 50
    },
    stateButtons: {
      display: 'flex',
      gap: 6,
      background: 'rgba(10, 14, 26, 0.9)',
      padding: '8px 12px',
      borderRadius: 8,
      backdropFilter: 'blur(12px)',
      border: `1px solid ${colors.cyan}30`,
      boxShadow: `0 0 30px rgba(0, 217, 255, 0.1), inset 0 0 20px rgba(0, 217, 255, 0.05)`
    },
    button: {
      padding: '8px 14px',
      border: `1px solid transparent`,
      borderRadius: 6,
      background: 'rgba(255, 255, 255, 0.05)',
      color: 'rgba(255, 255, 255, 0.5)',
      cursor: 'pointer',
      fontSize: 11,
      fontWeight: 500,
      fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
      letterSpacing: '0.1em',
      transition: 'all 0.2s ease',
      textTransform: 'uppercase'
    },
    micButton: {
      width: 60,
      height: 60,
      borderRadius: '50%',
      border: `2px solid ${colors.cyan}50`,
      background: `${colors.cyan}15`,
      color: colors.cyan,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s ease',
      boxShadow: `0 0 20px ${colors.cyan}30, inset 0 0 15px ${colors.cyan}10`
    },
    micButtonActive: {
      background: `${colors.cyan}30`,
      borderColor: colors.cyan,
      boxShadow: `0 0 40px ${colors.cyan}50, inset 0 0 20px ${colors.cyan}20`,
      animation: 'pulse-glow 1.5s ease-in-out infinite'
    },
    audioMeter: {
      position: 'fixed',
      right: 24,
      top: '50%',
      transform: 'translateY(-50%)',
      width: 3,
      height: 180,
      background: `${colors.cyan}10`,
      borderRadius: 3,
      overflow: 'hidden',
      border: `1px solid ${colors.cyan}30`,
      boxShadow: `0 0 15px ${colors.cyan}20`
    },
    audioMeterFill: {
      position: 'absolute',
      bottom: 0,
      left: 0,
      width: '100%',
      borderRadius: 3,
      transition: 'height 0.05s ease-out'
    },
    stateIndicator: {
      position: 'fixed',
      top: 60,
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '8px 16px',
      background: 'rgba(10, 14, 26, 0.8)',
      borderRadius: 6,
      backdropFilter: 'blur(12px)',
      border: `1px solid ${currentColor}40`
    },
    stateDot: {
      width: 8,
      height: 8,
      borderRadius: '50%',
      transition: 'all 0.3s ease'
    },
    stateLabel: {
      fontSize: 10,
      textTransform: 'uppercase',
      letterSpacing: '0.2em',
      fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
      fontWeight: 500,
      transition: 'color 0.3s ease'
    }
  }

  return (
    <>
      {/* State indicator */}
      <div style={styles.stateIndicator}>
        <div
          style={{
            ...styles.stateDot,
            background: currentColor,
            boxShadow: `0 0 12px ${currentColor}, 0 0 4px ${currentColor}`
          }}
        />
        <span style={{
          ...styles.stateLabel,
          color: currentColor,
          textShadow: `0 0 8px ${currentColor}66`
        }}>{state}</span>
      </div>

      {/* Main controls */}
      <div style={styles.container}>
        {/* Microphone button */}
        <button
          onClick={onAudioToggle}
          style={{
            ...styles.micButton,
            ...(isAudioActive ? styles.micButtonActive : {})
          }}
          title={isAudioActive ? 'Stop listening' : 'Start listening'}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {isAudioActive ? (
              // Stop icon
              <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
            ) : (
              // Mic icon
              <>
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </>
            )}
          </svg>
        </button>

        {/* State buttons */}
        <div style={styles.stateButtons}>
          {states.map((s) => {
            const buttonColor = stateColors[s] || colors.cyan
            const isActive = state === s
            return (
              <button
                key={s}
                onClick={() => onStateChange(s)}
                style={{
                  ...styles.button,
                  ...(isActive ? {
                    background: `${buttonColor}25`,
                    color: buttonColor,
                    borderColor: `${buttonColor}60`,
                    boxShadow: `0 0 15px ${buttonColor}30, inset 0 0 10px ${buttonColor}10`,
                    textShadow: `0 0 8px ${buttonColor}66`
                  } : {})
                }}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* Audio level meter */}
      {isAudioActive && (
        <div style={styles.audioMeter}>
          <div
            style={{
              ...styles.audioMeterFill,
              height: `${audioLevel * 100}%`,
              background: `linear-gradient(to top, ${colors.cyan}, ${colors.purple})`,
              boxShadow: `0 0 ${10 + audioLevel * 15}px ${colors.cyan}`
            }}
          />
        </div>
      )}

      {/* Custom keyframes for neon pulse */}
      <style>
        {`
          @keyframes pulse-glow {
            0%, 100% {
              transform: scale(1);
              box-shadow: 0 0 40px ${colors.cyan}50, inset 0 0 20px ${colors.cyan}20;
            }
            50% {
              transform: scale(1.05);
              box-shadow: 0 0 60px ${colors.cyan}70, inset 0 0 30px ${colors.cyan}30;
            }
          }
        `}
      </style>
    </>
  )
}
