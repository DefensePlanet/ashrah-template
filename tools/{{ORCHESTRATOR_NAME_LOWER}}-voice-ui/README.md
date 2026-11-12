# {{ORCHESTRATOR_NAME}} Voice Indicator Prototype

A browser-based prototype for the {{ORCHESTRATOR_NAME}} AI voice indicator - a glowing orb with organic movement and audio reactivity.

## Quick Start

```bash
cd {{CATALYST_ROOT}}/capsules/catalyst-system-ops/{{ORCHESTRATOR_NAME_LOWER}}-voice-ui
npm install
npm run dev
```

The prototype will open at `http://localhost:5173`

## States

The orb has four distinct states, each with unique visual characteristics:

| State | Color | Behavior |
|-------|-------|----------|
| **Idle** | Blue (#4a9eff) | Gentle breathing/pulsing, slow orbit camera |
| **Listening** | Green (#4affb8) | Reactive to microphone input, increased activity |
| **Speaking** | Purple (#9a6eff) | Animated response to simulated speech output |
| **Thinking** | Gold (#ffb84a) | Concentrated swirling effect |

## Controls

- **State Buttons**: Click to switch between idle/listening/speaking/thinking
- **Microphone Button**: Toggle real microphone input (requires permission)
- **Mouse Drag**: Orbit around the orb (disabled in idle state due to auto-rotate)
- **Scroll**: Zoom in/out

## Technical Details

### Shader Architecture

The orb uses custom GLSL shaders with:

1. **Simplex Noise (3D)** - Stefan Gustavson's optimized implementation
2. **Fractal Brownian Motion (FBM)** - Multi-octave noise for organic patterns
3. **Fresnel Effect** - Edge glow based on viewing angle
4. **Displacement Mapping** - Vertex-based morphing along normals

### Audio Processing

- Uses Web Audio API with `AnalyserNode`
- Calculates RMS (root mean square) for accurate amplitude
- Boosts sensitivity in human voice frequency range (85-500 Hz)
- Smooth interpolation to prevent jittery movement

### Key Uniforms

```glsl
uniform float uTime;              // Animation time
uniform float uAudioLevel;        // 0-1 audio amplitude
uniform int uState;               // 0=idle, 1=listening, 2=speaking, 3=thinking
uniform float uMorphSpeed;        // Noise animation speed
uniform float uDisplacementStrength; // Vertex displacement amount
uniform vec3 uBaseColor;          // Core orb color
uniform vec3 uGlowColor;          // Rim glow color
uniform vec3 uAccentColor;        // Highlight color
```

## Porting to SwiftUI/Metal

When porting to macOS:

1. **Metal Shaders**: Translate GLSL to MSL (Metal Shading Language)
   - Noise functions translate directly
   - Replace `gl_Position` with return value from vertex function
   - Replace `gl_FragColor` with return value from fragment function

2. **Geometry**: Use `MDLMesh` or `SCNGeometry` for the icosahedron

3. **Audio**: Replace Web Audio API with `AVAudioEngine`:
   ```swift
   let audioEngine = AVAudioEngine()
   let inputNode = audioEngine.inputNode
   inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, time in
       // Calculate RMS from buffer
   }
   ```

4. **Color Scheme**: The hex colors can be used directly in SwiftUI:
   ```swift
   Color(hex: "4a9eff")  // Idle blue
   Color(hex: "4affb8")  // Listening green
   Color(hex: "9a6eff")  // Speaking purple
   Color(hex: "ffb84a")  // Thinking gold
   ```

## File Structure

```
{{ORCHESTRATOR_NAME_LOWER}}-voice-ui/
├── index.html
├── package.json
├── vite.config.js
├── README.md
└── src/
    ├── main.jsx
    ├── App.jsx
    └── components/
        ├── {{ORCHESTRATOR_NAME}}Orb.jsx      # Core orb with shaders
        ├── Controls.jsx       # UI controls
        └── AudioProcessor.jsx # Web Audio API integration
```

## Dependencies

- React 18
- Three.js 0.160
- @react-three/fiber 8.15
- @react-three/drei 9.92
- Vite 5.0
