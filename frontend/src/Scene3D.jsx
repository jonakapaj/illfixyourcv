import { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// Draws a stylised CV page onto a canvas so the 3D sheets look like documents.
function makePageTexture(accent, ink, variant) {
  const c = document.createElement('canvas');
  c.width = 512; c.height = 724;
  const g = c.getContext('2d');
  g.fillStyle = '#ffffff';
  g.fillRect(0, 0, c.width, c.height);
  const bar = (x, y, w, h, color, r = 6) => {
    g.fillStyle = color;
    g.beginPath(); g.roundRect(x, y, w, h, r); g.fill();
  };
  if (variant === 0) {
    bar(48, 52, 230, 26, ink);
    bar(48, 92, 150, 12, accent);
  } else {
    bar(0, 0, 512, 120, ink, 0);
    bar(48, 44, 210, 22, '#ffffff');
  }
  let y = variant === 0 ? 150 : 170;
  for (let s = 0; s < 4; s++) {
    bar(48, y, 120, 12, accent); y += 30;
    const lines = 3 + ((s + variant) % 2);
    for (let i = 0; i < lines; i++) {
      g.fillStyle = '#c9ced8';
      g.beginPath(); g.arc(56, y + 5, 4, 0, Math.PI * 2); g.fill();
      bar(72, y, 340 - ((i * 53 + s * 31) % 140), 10, '#d5d9e1');
      y += 24;
    }
    y += 20;
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function Sheet({ position, rotation, texture, scale = 1, shade = 1 }) {
  return (
    <group position={position} rotation={rotation} scale={scale}>
      <mesh>
        <boxGeometry args={[2.1, 2.97, 0.03]} />
        <meshStandardMaterial color="#ffffff" roughness={0.65} />
      </mesh>
      <mesh position={[0, 0, 0.017]}>
        <planeGeometry args={[2.02, 2.89]} />
        {/* Unlit so the paper reads as white, not grey */}
        <meshBasicMaterial map={texture} color={new THREE.Color(shade, shade, shade)} toneMapped={false} />
      </mesh>
    </group>
  );
}

function ScanBeam({ accent, speed }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime() * speed;
    ref.current.position.y = Math.sin(t) * 1.35;
    ref.current.material.opacity = 0.28 + 0.12 * Math.sin(t * 3);
  });
  return (
    <mesh ref={ref} position={[0, 0, 0.09]}>
      <planeGeometry args={[2.0, 0.05]} />
      <meshBasicMaterial color={accent} transparent opacity={0.35} toneMapped={false} />
    </mesh>
  );
}

// Slow bobbing motion (replaces drei's <Float> to keep the bundle small).
function Float({ children, speed }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime() * speed;
    ref.current.position.y = Math.sin(t * 0.9) * 0.08;
    ref.current.rotation.z = Math.sin(t * 0.6) * 0.03;
  });
  return <group ref={ref}>{children}</group>;
}

function Rig({ children, speed }) {
  const ref = useRef();
  useFrame(({ clock, pointer }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    // Gentle idle sway plus a little parallax toward the mouse.
    ref.current.rotation.y = THREE.MathUtils.lerp(ref.current.rotation.y, -0.42 + pointer.x * 0.18 + Math.sin(t * 0.3 * speed) * 0.05, 0.05);
    ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, 0.12 - pointer.y * 0.1, 0.05);
  });
  return <group ref={ref}>{children}</group>;
}

function Scene({ accent, ink, busy }) {
  const [front, back] = useMemo(
    () => [makePageTexture(accent, ink, 0), makePageTexture(accent, ink, 1)],
    [accent, ink],
  );
  const speed = busy ? 2.6 : 1;
  return (
    <>
      <ambientLight intensity={0.85} />
      <directionalLight position={[3, 4, 5]} intensity={1.2} />
      <directionalLight position={[-4, -2, 2]} intensity={0.35} color={accent} />
      <Rig speed={speed}>
        <Float speed={1.4 * speed}>
          <Sheet position={[0.75, 0.25, -0.55]} rotation={[0, 0, 0.06]} texture={back} scale={0.94} shade={0.9} />
          <group position={[-0.3, -0.1, 0]} rotation={[0, 0, -0.04]}>
            <Sheet position={[0, 0, 0]} rotation={[0, 0, 0]} texture={front} />
            <ScanBeam accent={accent} speed={speed} />
          </group>
        </Float>
      </Rig>
    </>
  );
}

export default function Scene3D({ accent = '#2f4bff', ink = '#0f1115', busy = false, className = '' }) {
  const reduced = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0, 5.2], fov: 38 }}
        frameloop={reduced ? 'demand' : 'always'}
        gl={{ antialias: true, alpha: true }}
      >
        <Scene accent={accent} ink={ink} busy={busy} />
      </Canvas>
    </div>
  );
}
