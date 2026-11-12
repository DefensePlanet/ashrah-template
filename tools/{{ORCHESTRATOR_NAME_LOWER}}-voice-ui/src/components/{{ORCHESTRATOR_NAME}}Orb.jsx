import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// Simplex 3D Noise - by Stefan Gustavson (optimized)
const noiseGLSL = `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}

// Fractal Brownian Motion for more organic patterns
float fbm(vec3 p, int octaves) {
  float value = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;
  for(int i = 0; i < 6; i++) {
    if(i >= octaves) break;
    value += amplitude * snoise(p * frequency);
    amplitude *= 0.5;
    frequency *= 2.0;
  }
  return value;
}
`

// Vertex shader - displacement and morphing
const vertexShader = `
${noiseGLSL}

uniform float uTime;
uniform float uAudioLevel;
uniform int uState; // 0=idle, 1=listening, 2=speaking, 3=thinking
uniform float uMorphSpeed;
uniform float uDisplacementStrength;

varying vec3 vNormal;
varying vec3 vPosition;
varying float vDisplacement;
varying float vFresnel;

void main() {
  vec3 pos = position;

  // Base displacement parameters by state
  float baseSpeed = uMorphSpeed;
  float baseStrength = uDisplacementStrength;
  float noiseScale = 1.5;

  // State-specific modifications
  if (uState == 0) {
    // Idle: gentle breathing
    baseSpeed *= 0.3;
    baseStrength *= 0.15;
    noiseScale = 1.0;
  } else if (uState == 1) {
    // Listening: reactive to audio
    baseSpeed *= 0.8;
    baseStrength *= 0.3 + uAudioLevel * 0.5;
    noiseScale = 1.5 + uAudioLevel * 0.5;
  } else if (uState == 2) {
    // Speaking: pulsing with speech
    baseSpeed *= 1.2;
    baseStrength *= 0.25 + uAudioLevel * 0.4;
    noiseScale = 2.0;
  } else if (uState == 3) {
    // Thinking: concentrated swirling
    baseSpeed *= 2.0;
    baseStrength *= 0.35;
    noiseScale = 2.5;
  }

  // Multi-layered noise displacement
  float time = uTime * baseSpeed;

  // Primary displacement - large features
  float noise1 = fbm(pos * noiseScale + time * 0.3, 3);

  // Secondary displacement - medium detail
  float noise2 = snoise(pos * noiseScale * 2.0 + time * 0.5) * 0.5;

  // Tertiary displacement - fine detail
  float noise3 = snoise(pos * noiseScale * 4.0 + time * 0.8) * 0.25;

  // Combine noise layers
  float displacement = (noise1 + noise2 + noise3) * baseStrength;

  // Add audio reactivity pulse
  if (uState == 1 || uState == 2) {
    float audioPulse = uAudioLevel * 0.15 * sin(uTime * 8.0 + length(pos) * 3.0);
    displacement += audioPulse;
  }

  // Thinking state: add swirl pattern
  if (uState == 3) {
    float angle = atan(pos.x, pos.z);
    float swirl = sin(angle * 3.0 + uTime * 3.0 + pos.y * 2.0) * 0.1;
    displacement += swirl;
  }

  // Apply displacement along normal
  vec3 newPosition = pos + normal * displacement;

  // Recalculate normal (approximate)
  vec3 tangent = normalize(cross(normal, vec3(0.0, 1.0, 0.0)));
  if (length(tangent) < 0.001) tangent = normalize(cross(normal, vec3(1.0, 0.0, 0.0)));
  vec3 bitangent = normalize(cross(normal, tangent));

  float eps = 0.001;
  float d1 = fbm((pos + tangent * eps) * noiseScale + time * 0.3, 3) * baseStrength;
  float d2 = fbm((pos + bitangent * eps) * noiseScale + time * 0.3, 3) * baseStrength;

  vec3 p1 = pos + tangent * eps + normal * d1;
  vec3 p2 = pos + bitangent * eps + normal * d2;

  vec3 newNormal = normalize(cross(p2 - newPosition, p1 - newPosition));

  // Calculate fresnel for glow effect
  vec4 mvPosition = modelViewMatrix * vec4(newPosition, 1.0);
  vec3 viewDir = normalize(-mvPosition.xyz);
  vFresnel = pow(1.0 - abs(dot(viewDir, normalize(normalMatrix * newNormal))), 2.0);

  // Pass to fragment shader
  vNormal = normalize(normalMatrix * newNormal);
  vPosition = (modelMatrix * vec4(newPosition, 1.0)).xyz;
  vDisplacement = displacement;

  gl_Position = projectionMatrix * mvPosition;
}
`

// Fragment shader - glowing effect
const fragmentShader = `
uniform float uTime;
uniform float uAudioLevel;
uniform int uState;
uniform vec3 uBaseColor;
uniform vec3 uGlowColor;
uniform vec3 uAccentColor;

varying vec3 vNormal;
varying vec3 vPosition;
varying float vDisplacement;
varying float vFresnel;

void main() {
  // Dynamic color based on state
  vec3 coreColor = uBaseColor;
  vec3 glowColor = uGlowColor;

  // State color modifications
  float colorIntensity = 1.0;
  if (uState == 0) {
    colorIntensity = 0.6;
  } else if (uState == 1) {
    colorIntensity = 0.8 + uAudioLevel * 0.4;
    glowColor = mix(glowColor, uAccentColor, uAudioLevel * 0.5);
  } else if (uState == 2) {
    colorIntensity = 0.9 + uAudioLevel * 0.3;
    coreColor = mix(coreColor, uAccentColor, 0.3);
  } else if (uState == 3) {
    colorIntensity = 0.7 + sin(uTime * 2.0) * 0.15;
    float swirl = sin(atan(vPosition.x, vPosition.z) * 4.0 + uTime * 3.0) * 0.5 + 0.5;
    coreColor = mix(coreColor, uAccentColor, swirl * 0.4);
  }

  // Fresnel-based glow
  float fresnel = vFresnel;

  // Inner glow gradient
  float innerGlow = pow(1.0 - fresnel, 3.0) * 0.5;

  // Outer rim glow
  float rimGlow = pow(fresnel, 1.5) * colorIntensity;

  // Displacement-based color variation
  float dispColor = vDisplacement * 2.0 + 0.5;

  // Combine colors
  vec3 finalColor = coreColor * innerGlow;
  finalColor += glowColor * rimGlow;
  finalColor += uAccentColor * dispColor * 0.2;

  // Pulsing core brightness
  float pulse = sin(uTime * 2.0) * 0.1 + 0.9;
  if (uState == 2) {
    pulse = 0.8 + uAudioLevel * 0.4;
  }
  finalColor *= pulse;

  // Add subtle noise texture
  float noiseTexture = fract(sin(dot(vPosition.xy, vec2(12.9898, 78.233))) * 43758.5453);
  finalColor += noiseTexture * 0.02;

  // Alpha based on fresnel for soft edges
  float alpha = 0.85 + fresnel * 0.15;

  gl_FragColor = vec4(finalColor * colorIntensity, alpha);
}
`

// Outer glow shader
const glowVertexShader = `
varying vec3 vNormal;
varying vec3 vPosition;

void main() {
  vNormal = normalize(normalMatrix * normal);
  vPosition = (modelMatrix * vec4(position, 1.0)).xyz;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

const glowFragmentShader = `
uniform vec3 uGlowColor;
uniform float uGlowIntensity;
uniform float uAudioLevel;
uniform int uState;

varying vec3 vNormal;
varying vec3 vPosition;

void main() {
  vec3 viewDirection = normalize(cameraPosition - vPosition);
  float fresnel = dot(viewDirection, vNormal);
  fresnel = pow(fresnel, 4.0);

  float intensity = uGlowIntensity;
  if (uState == 1) {
    intensity *= 1.0 + uAudioLevel * 0.5;
  } else if (uState == 2) {
    intensity *= 1.2 + uAudioLevel * 0.4;
  } else if (uState == 3) {
    intensity *= 1.3;
  }

  float glow = fresnel * intensity;

  gl_FragColor = vec4(uGlowColor, glow * 0.6);
}
`

// Color schemes for different states
const COLOR_SCHEMES = {
  idle: {
    base: new THREE.Color('#1a4a6e'),
    glow: new THREE.Color('#4a9eff'),
    accent: new THREE.Color('#00d4ff')
  },
  listening: {
    base: new THREE.Color('#1a5a4e'),
    glow: new THREE.Color('#4affb8'),
    accent: new THREE.Color('#00ffc8')
  },
  speaking: {
    base: new THREE.Color('#4a3a6e'),
    glow: new THREE.Color('#9a6eff'),
    accent: new THREE.Color('#c084fc')
  },
  thinking: {
    base: new THREE.Color('#5a4a2e'),
    glow: new THREE.Color('#ffb84a'),
    accent: new THREE.Color('#ffd700')
  }
}

const STATE_INDEX = { idle: 0, listening: 1, speaking: 2, thinking: 3 }

export default function {{ORCHESTRATOR_NAME}}Orb({ state = 'idle', audioLevel = 0 }) {
  const meshRef = useRef()
  const glowRef = useRef()
  const materialRef = useRef()
  const glowMaterialRef = useRef()

  // Create high-detail sphere geometry
  const geometry = useMemo(() => {
    return new THREE.IcosahedronGeometry(1, 64)
  }, [])

  const glowGeometry = useMemo(() => {
    return new THREE.IcosahedronGeometry(1.15, 32)
  }, [])

  // Create shader materials
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uAudioLevel: { value: 0 },
        uState: { value: 0 },
        uMorphSpeed: { value: 1.0 },
        uDisplacementStrength: { value: 0.3 },
        uBaseColor: { value: COLOR_SCHEMES.idle.base },
        uGlowColor: { value: COLOR_SCHEMES.idle.glow },
        uAccentColor: { value: COLOR_SCHEMES.idle.accent }
      },
      transparent: true,
      side: THREE.DoubleSide
    })
  }, [])

  const glowMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: glowVertexShader,
      fragmentShader: glowFragmentShader,
      uniforms: {
        uGlowColor: { value: COLOR_SCHEMES.idle.glow },
        uGlowIntensity: { value: 0.5 },
        uAudioLevel: { value: 0 },
        uState: { value: 0 }
      },
      transparent: true,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  }, [])

  // Animation loop
  useFrame((_, delta) => {
    if (materialRef.current && glowMaterialRef.current) {
      // Update time
      materialRef.current.uniforms.uTime.value += delta

      // Smooth audio level interpolation
      const currentAudio = materialRef.current.uniforms.uAudioLevel.value
      const targetAudio = audioLevel
      const smoothAudio = currentAudio + (targetAudio - currentAudio) * 0.15

      materialRef.current.uniforms.uAudioLevel.value = smoothAudio
      glowMaterialRef.current.uniforms.uAudioLevel.value = smoothAudio

      // Update state
      const stateIndex = STATE_INDEX[state] || 0
      materialRef.current.uniforms.uState.value = stateIndex
      glowMaterialRef.current.uniforms.uState.value = stateIndex

      // Smooth color transitions
      const colors = COLOR_SCHEMES[state] || COLOR_SCHEMES.idle
      materialRef.current.uniforms.uBaseColor.value.lerp(colors.base, 0.05)
      materialRef.current.uniforms.uGlowColor.value.lerp(colors.glow, 0.05)
      materialRef.current.uniforms.uAccentColor.value.lerp(colors.accent, 0.05)
      glowMaterialRef.current.uniforms.uGlowColor.value.lerp(colors.glow, 0.05)
    }
  })

  return (
    <group>
      {/* Main orb */}
      <mesh ref={meshRef} geometry={geometry}>
        <primitive object={material} ref={materialRef} attach="material" />
      </mesh>

      {/* Outer glow */}
      <mesh ref={glowRef} geometry={glowGeometry}>
        <primitive object={glowMaterial} ref={glowMaterialRef} attach="material" />
      </mesh>
    </group>
  )
}
