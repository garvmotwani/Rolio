'use client';

import { useRef, useMemo, useCallback, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

/* ─── Single Particle ─── */
function Particle({ position, size, speed, phase }: {
  position: [number, number, number];
  size: number;
  speed: number;
  phase: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const initialPos = useMemo(() => new THREE.Vector3(...position), [position]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime() * speed;
    ref.current.position.x = initialPos.x + Math.sin(t + phase) * 0.3;
    ref.current.position.y = initialPos.y + Math.cos(t * 0.7 + phase) * 0.2;
    ref.current.position.z = initialPos.z + Math.sin(t * 0.5 + phase * 2) * 0.15;
  });

  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[size, 16, 16]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
    </mesh>
  );
}

/* ─── Connection Lines ─── */
function ConnectionLines({ count }: { count: number }) {
  const ref = useRef<THREE.LineSegments>(null);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * count * 6);
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, [count]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const positions = ref.current.geometry.attributes.position as THREE.BufferAttribute;
    const t = clock.getElapsedTime();

    let idx = 0;
    for (let i = 0; i < Math.min(count, 30); i++) {
      for (let j = i + 1; j < Math.min(count, 30); j++) {
        const angle_i = (i / count) * Math.PI * 2;
        const angle_j = (j / count) * Math.PI * 2;
        const radius = 2.5;

        const x1 = Math.cos(angle_i + t * 0.05) * radius + Math.sin(t * 0.1 + i) * 0.3;
        const y1 = Math.sin(angle_i + t * 0.05) * radius * 0.6 + Math.cos(t * 0.08 + i) * 0.2;
        const z1 = Math.sin(angle_i * 0.5 + t * 0.03) * 0.8;

        const x2 = Math.cos(angle_j + t * 0.05) * radius + Math.sin(t * 0.1 + j) * 0.3;
        const y2 = Math.sin(angle_j + t * 0.05) * radius * 0.6 + Math.cos(t * 0.08 + j) * 0.2;
        const z2 = Math.sin(angle_j * 0.5 + t * 0.03) * 0.8;

        const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2);

        if (dist < 3.5) {
          positions.array[idx++] = x1;
          positions.array[idx++] = y1;
          positions.array[idx++] = z1;
          positions.array[idx++] = x2;
          positions.array[idx++] = y2;
          positions.array[idx++] = z2;
        }
      }
    }

    // Zero out remaining
    for (; idx < positions.array.length; idx++) {
      positions.array[idx] = 0;
    }

    positions.needsUpdate = true;
  });

  return (
    <lineSegments ref={ref} geometry={geometry}>
      <lineBasicMaterial color="#ffffff" transparent opacity={0.06} />
    </lineSegments>
  );
}

/* ─── Orbiting Ring ─── */
function OrbitRing({ radius, speed, rotationX, opacity }: {
  radius: number;
  speed: number;
  rotationX: number;
  opacity: number;
}) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.z = clock.getElapsedTime() * speed;
  });

  return (
    <mesh ref={ref} rotation={[rotationX, 0, 0]}>
      <torusGeometry args={[radius, 0.005, 8, 128]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={opacity} />
    </mesh>
  );
}

/* ─── Central Glow ─── */
function CenterGlow() {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const scale = 1 + Math.sin(clock.getElapsedTime() * 1.5) * 0.08;
    ref.current.scale.setScalar(scale);
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.25, 32, 32]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.8} />
    </mesh>
  );
}

/* ─── Mouse-reactive Particles ─── */
function MouseParticles() {
  const groupRef = useRef<THREE.Group>(null);
  const { viewport } = useThree();
  const mouse = useRef({ x: 0, y: 0 });

  useFrame(({ pointer }) => {
    if (!groupRef.current) return;
    mouse.current.x = pointer.x * viewport.width * 0.5;
    mouse.current.y = pointer.y * viewport.height * 0.5;
    groupRef.current.rotation.y = THREE.MathUtils.lerp(
      groupRef.current.rotation.y,
      mouse.current.x * 0.05,
      0.05
    );
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      mouse.current.y * 0.03,
      0.05
    );
  });

  const particleData = useMemo(() => {
    const data: Array<{
      position: [number, number, number];
      size: number;
      speed: number;
      phase: number;
    }> = [];

    // Companies ring (outer)
    const companies = ['G', 'S', 'F', 'V', 'N', 'M'];
    companies.forEach((_, i) => {
      const angle = (i / companies.length) * Math.PI * 2;
      data.push({
        position: [Math.cos(angle) * 3, Math.sin(angle) * 1.8, (Math.random() - 0.5) * 0.5],
        size: 0.06,
        speed: 0.3 + Math.random() * 0.2,
        phase: i * 1.1,
      });
    });

    // Skills ring (mid)
    const skills = ['Py', 'JS', 'TS', 'R', 'N', 'S', 'Go', 'R'];
    skills.forEach((_, i) => {
      const angle = (i / skills.length) * Math.PI * 2;
      data.push({
        position: [Math.cos(angle) * 2, Math.sin(angle) * 1.2, (Math.random() - 0.5) * 0.3],
        size: 0.04,
        speed: 0.4 + Math.random() * 0.3,
        phase: i * 0.9 + 3,
      });
    });

    // Small scattered particles
    for (let i = 0; i < 40; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;
      const r = 1 + Math.random() * 3;
      data.push({
        position: [
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta) * 0.6,
          r * Math.cos(phi) * 0.3,
        ],
        size: 0.01 + Math.random() * 0.025,
        speed: 0.2 + Math.random() * 0.5,
        phase: Math.random() * Math.PI * 2,
      });
    }

    return data;
  }, []);

  return (
    <group ref={groupRef}>
      {particleData.map((p, i) => (
        <Particle key={i} {...p} />
      ))}
    </group>
  );
}

/* ─── Scene ─── */
function Scene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <MouseParticles />
      <ConnectionLines count={20} />
      <OrbitRing radius={3.2} speed={0.08} rotationX={Math.PI * 0.4} opacity={0.04} />
      <OrbitRing radius={2.0} speed={-0.12} rotationX={Math.PI * 0.6} opacity={0.03} />
      <OrbitRing radius={4.2} speed={0.05} rotationX={Math.PI * 0.3} opacity={0.02} />
    </>
  );
}

/* ─── Canvas Wrapper ─── */
export default function ParticleHero() {
  return (
    <div className="absolute inset-0">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <Suspense fallback={null}>
          <Scene />
        </Suspense>
      </Canvas>
    </div>
  );
}
