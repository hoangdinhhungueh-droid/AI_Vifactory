import React, { useEffect, useRef } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

/**
 * EvidenceProp3D - Procedural 3D Japanese/Asian Hanko Seal (Red Stamp).
 * Upgraded to Vox Style Tactical Paper-Collage Architecture:
 * - 12fps Stop-Motion physics quantization (steppedFrame) per Vox Motion standard.
 * - Archival forensic evidence specimen mount with frosted scotch tape.
 * - Zero external GLB/mesh assets, 100% deterministic frame-by-frame rendering.
 * - Cel-shading / Comic Noir aesthetic per Rule 122 & Rule 435.
 */
export const EvidenceProp3D: React.FC<{
  title?: string;
  subtitle?: string;
  theme?: "vox_paper" | "noir_dossier" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;
}> = ({
  title = "CONFIDENTIAL EVIDENCE // EXHIBIT A",
  subtitle = "IMPERIAL SEAL / AUTHENTICATION STAMP",
  theme = "noir_dossier",
  layout = "full_bleed_focus",
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Stop-motion physics (10fps feel on 30fps timeline - integer hold 3 per Vox Style)
  const steppedFrame = Math.floor(frame / 3) * 3;

  // Spring entrance with paper overshoot
  const entrance = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 140 },
  });

  const opacity = interpolate(steppedFrame, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isNoir = theme !== "vox_paper";
  const paperBg = isNoir ? "#111827" : "#faf7ee";
  const textColor = isNoir ? "#f3f4f6" : "#1e293b";
  const subtleColor = isNoir ? "#9ca3af" : "#64748b";
  const borderColor = isNoir ? "#374151" : "#e2d9c2";
  const stampBorderColor = isNoir ? "#ef4444" : "#b91c1c";

  const sceneRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    modelGroup: THREE.Group;
    lights: { keyLight: THREE.DirectionalLight; rimLight: THREE.DirectionalLight };
    geometries: THREE.BufferGeometry[];
    materials: THREE.Material[];
  } | null>(null);

  // Initialize WebGL context and 3D scene ONCE on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true,
        powerPreference: "high-performance",
      });
    } catch (e) {
      console.warn("[EvidenceProp3D] Failed to create WebGLRenderer:", e);
      return;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);

    const ambientLight = new THREE.AmbientLight(0x222733, 1.4);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfffaed, 2.8);
    keyLight.position.set(5, 8, 5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xffeedd, 1.8);
    rimLight.position.set(-6, 4, -5);
    scene.add(rimLight);

    const redGlow = new THREE.PointLight(0xd32f2f, 2.2, 6);
    redGlow.position.set(0, 0.2, 0);
    scene.add(redGlow);

    const modelGroup = new THREE.Group();
    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.Material[] = [];

    // Materials
    const blackLacquer = new THREE.MeshToonMaterial({ color: 0x181920 });
    const goldAccent = new THREE.MeshToonMaterial({ color: 0xd4af37 });
    const vermilionRed = new THREE.MeshToonMaterial({ color: 0xd32f2f });
    const inkOutlineMat = new THREE.MeshBasicMaterial({ color: 0x050608, side: THREE.BackSide });
    materials.push(blackLacquer, goldAccent, vermilionRed, inkOutlineMat);

    // 1. Hanko Handle
    const handleGeo = new THREE.CylinderGeometry(0.55, 0.65, 2.8, 32);
    geometries.push(handleGeo);
    const handleMesh = new THREE.Mesh(handleGeo, blackLacquer);
    handleMesh.position.y = 1.6;
    handleMesh.castShadow = true;
    modelGroup.add(handleMesh);

    const handleOutlineGeo = new THREE.CylinderGeometry(0.59, 0.69, 2.84, 32);
    geometries.push(handleOutlineGeo);
    const handleOutline = new THREE.Mesh(handleOutlineGeo, inkOutlineMat);
    handleOutline.position.y = 1.6;
    modelGroup.add(handleOutline);

    // 2. Cap
    const capGeo = new THREE.SphereGeometry(0.55, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    geometries.push(capGeo);
    const capMesh = new THREE.Mesh(capGeo, blackLacquer);
    capMesh.position.y = 3.0;
    modelGroup.add(capMesh);

    // 3. Gold Rings
    const ring1Geo = new THREE.TorusGeometry(0.58, 0.04, 16, 32);
    const ring2Geo = new THREE.TorusGeometry(0.66, 0.05, 16, 32);
    geometries.push(ring1Geo, ring2Geo);
    const ring1 = new THREE.Mesh(ring1Geo, goldAccent);
    ring1.rotation.x = Math.PI / 2;
    ring1.position.y = 2.8;
    modelGroup.add(ring1);

    const ring2 = new THREE.Mesh(ring2Geo, goldAccent);
    ring2.rotation.x = Math.PI / 2;
    ring2.position.y = 0.5;
    modelGroup.add(ring2);

    // 4. Base Stamp
    const baseGeo = new THREE.CylinderGeometry(0.75, 0.75, 0.4, 32);
    const baseOutlineGeo = new THREE.CylinderGeometry(0.79, 0.79, 0.44, 32);
    geometries.push(baseGeo, baseOutlineGeo);
    const baseMesh = new THREE.Mesh(baseGeo, vermilionRed);
    baseMesh.position.y = 0.2;
    baseMesh.castShadow = true;
    modelGroup.add(baseMesh);

    const baseOutline = new THREE.Mesh(baseOutlineGeo, inkOutlineMat);
    baseOutline.position.y = 0.2;
    modelGroup.add(baseOutline);

    // 5. Stage Ground
    const groundGeo = new THREE.PlaneGeometry(12, 12);
    const groundMat = new THREE.MeshToonMaterial({ color: 0x0c0f17 });
    geometries.push(groundGeo);
    materials.push(groundMat);
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = 0;
    ground.receiveShadow = true;
    scene.add(ground);

    scene.add(modelGroup);

    sceneRef.current = {
      renderer,
      scene,
      camera,
      modelGroup,
      lights: { keyLight, rimLight },
      geometries,
      materials,
    };

    return () => {
      try {
        geometries.forEach((g) => g.dispose());
        materials.forEach((m) => m.dispose());
        renderer.dispose();
      } catch (err) {
        // cleanup safe
      }
      sceneRef.current = null;
    };
  }, [width, height]);

  // Frame-by-frame animation update (NO WebGL context recreation)
  useEffect(() => {
    const s = sceneRef.current;
    if (!s) return;

    const orbitAngle = interpolate(
      steppedFrame,
      [0, 90],
      [-Math.PI * 0.25, Math.PI * 0.45],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    const cameraDist = 8.5;
    const cameraY = interpolate(steppedFrame, [0, 45, 90], [2.2, 3.2, 2.4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    s.camera.position.set(
      Math.sin(orbitAngle) * cameraDist,
      cameraY,
      Math.cos(orbitAngle) * cameraDist
    );
    s.camera.lookAt(0, 0.8, 0);

    // Quantized 12fps stop-motion wobble
    const wobble = Math.sin(steppedFrame * 0.1) * 0.04;
    s.modelGroup.rotation.z = wobble;
    s.modelGroup.rotation.x = Math.cos(steppedFrame * 0.08) * 0.03;

    s.renderer.render(s.scene, s.camera);
  }, [steppedFrame]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        backgroundColor: paperBg,
        borderRadius: 6,
        overflow: "hidden",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        boxShadow: "0 25px 60px rgba(0,0,0,0.75), 0 5px 15px rgba(0,0,0,0.4)",
        border: `1px solid ${borderColor}`,
        opacity,
        transform: `scale(${entrance}) rotate(-0.5deg)`,
        transformOrigin: "center center",
      }}
    >
      {/* Scotch tape at top center per Vox Tactile standard */}
      <div
        style={{
          position: "absolute",
          top: -8,
          left: "50%",
          transform: "translateX(-50%) rotate(1.5deg)",
          width: 140,
          height: 28,
          backgroundColor: "rgba(255, 255, 255, 0.65)",
          border: "1px solid rgba(255, 255, 255, 0.75)",
          boxShadow: "0 2px 4px rgba(0,0,0,0.12)",
          zIndex: 40,
        }}
      />

      {/* Paper fold / fiber texture watermark */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: isNoir
            ? "linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(0,0,0,0.3) 100%)"
            : "linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(235,225,200,0.3) 100%)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* Three.js procedural canvas */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          zIndex: 2,
        }}
      />

      {/* Top Header: Physical Evidence Archive Tag */}
      <div
        style={{
          position: "absolute",
          top: 32,
          left: 40,
          borderLeft: `4px solid ${stampBorderColor}`,
          paddingLeft: 16,
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: 2,
            color: subtleColor,
            textTransform: "uppercase",
          }}
        >
          EVIDENCE ARCHIVE // FORENSIC SPECIMEN
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: "0.08em",
            color: textColor,
            textTransform: "uppercase",
            textShadow: "0 2px 8px rgba(0,0,0,0.8)",
            marginTop: 2,
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.12em",
            color: stampBorderColor,
            marginTop: 4,
          }}
        >
          {subtitle} // 12 FPS STOP-MOTION
        </div>
      </div>

      {/* Red Rubber Stamp Badge: Chain of Custody */}
      <div
        style={{
          position: "absolute",
          top: 28,
          right: 36,
          border: `2px solid ${stampBorderColor}`,
          borderRadius: 3,
          padding: "4px 12px",
          color: stampBorderColor,
          fontSize: 13,
          fontWeight: 900,
          letterSpacing: 2,
          transform: "rotate(5deg)",
          textTransform: "uppercase",
          backgroundColor: isNoir ? "rgba(239, 68, 68, 0.08)" : "rgba(185, 28, 28, 0.08)",
          boxShadow: "inset 0 0 4px rgba(185,28,28,0.2)",
          zIndex: 20,
        }}
      >
        CHAIN OF CUSTODY // VERIFIED
      </div>

      {/* Bottom Forensic Registry Footer */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          left: 40,
          right: 40,
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          color: subtleColor,
          letterSpacing: 1.2,
          borderTop: `1px solid ${borderColor}`,
          paddingTop: 8,
          zIndex: 20,
        }}
      >
        <div>SPECIMEN: PROCEDURAL HANKO ARTIFACT</div>
        <div>STOP-MOTION FRAME: {Math.floor(steppedFrame / 3)} / 36</div>
        <div>ARCHIVAL PROOF: ZERO-MESH 3D</div>
      </div>
    </div>
  );
};
