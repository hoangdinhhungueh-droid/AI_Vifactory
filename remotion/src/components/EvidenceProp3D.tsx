import React, { useEffect, useRef } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

/**
 * EvidenceProp3D - Procedural 3D Japanese/Asian Hanko Seal (Red Stamp).
 * Built with procedural Three.js geometry inspired by img2threejs principles.
 * Zero external GLB/mesh assets, 100% deterministic frame-by-frame rendering.
 * Cel-shading / Comic Noir aesthetic per Rule 122.
 */
export const EvidenceProp3D: React.FC<{
  title?: string;
  subtitle?: string;
}> = ({
  title = "CONFIDENTIAL EVIDENCE // EXHIBIT A",
  subtitle = "IMPERIAL SEAL / AUTHENTICATION STAMP",
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);

    const orbitAngle = interpolate(frame, [0, 90], [-Math.PI * 0.25, Math.PI * 0.45]);
    const cameraDist = 8.5;
    const cameraY = interpolate(frame, [0, 45, 90], [2.2, 3.2, 2.4]);
    camera.position.set(
      Math.sin(orbitAngle) * cameraDist,
      cameraY,
      Math.cos(orbitAngle) * cameraDist
    );
    camera.lookAt(0, 0.8, 0);

    const ambientLight = new THREE.AmbientLight(0x1a2233, 1.2);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffeedd, 2.5);
    keyLight.position.set(5, 8, 5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x00e5ff, 3.0);
    rimLight.position.set(-6, 4, -5);
    scene.add(rimLight);

    const redGlow = new THREE.PointLight(0xff1744, 2.0, 6);
    redGlow.position.set(0, 0.2, 0);
    scene.add(redGlow);

    const hankoGroup = new THREE.Group();

    const blackLacquer = new THREE.MeshToonMaterial({
      color: 0x181920,
      roughness: 0.2,
    });
    const goldAccent = new THREE.MeshToonMaterial({
      color: 0xd4af37,
      roughness: 0.3,
    });
    const vermilionRed = new THREE.MeshToonMaterial({
      color: 0xd32f2f,
      roughness: 0.4,
    });
    const inkOutlineMat = new THREE.MeshBasicMaterial({
      color: 0x050608,
      side: THREE.BackSide,
    });

    const handleGeo = new THREE.CylinderGeometry(0.55, 0.65, 2.8, 32);
    const handleMesh = new THREE.Mesh(handleGeo, blackLacquer);
    handleMesh.position.y = 1.6;
    handleMesh.castShadow = true;
    hankoGroup.add(handleMesh);

    const handleOutlineGeo = new THREE.CylinderGeometry(0.59, 0.69, 2.84, 32);
    const handleOutline = new THREE.Mesh(handleOutlineGeo, inkOutlineMat);
    handleOutline.position.y = 1.6;
    hankoGroup.add(handleOutline);

    const capGeo = new THREE.SphereGeometry(0.55, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    const capMesh = new THREE.Mesh(capGeo, blackLacquer);
    capMesh.position.y = 3.0;
    hankoGroup.add(capMesh);

    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.04, 16, 32), goldAccent);
    ring1.rotation.x = Math.PI / 2;
    ring1.position.y = 2.8;
    hankoGroup.add(ring1);

    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(0.66, 0.05, 16, 32), goldAccent);
    ring2.rotation.x = Math.PI / 2;
    ring2.position.y = 0.5;
    hankoGroup.add(ring2);

    const baseGeo = new THREE.CylinderGeometry(0.75, 0.75, 0.4, 32);
    const baseMesh = new THREE.Mesh(baseGeo, vermilionRed);
    baseMesh.position.y = 0.2;
    baseMesh.castShadow = true;
    hankoGroup.add(baseMesh);

    const baseOutline = new THREE.Mesh(
      new THREE.CylinderGeometry(0.79, 0.79, 0.44, 32),
      inkOutlineMat
    );
    baseOutline.position.y = 0.2;
    hankoGroup.add(baseOutline);

    const groundGeo = new THREE.PlaneGeometry(12, 12);
    const groundMat = new THREE.MeshToonMaterial({
      color: 0x0a0c12,
      roughness: 0.9,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = 0;
    ground.receiveShadow = true;
    scene.add(ground);

    scene.add(hankoGroup);

    const wobble = Math.sin(frame * 0.1) * 0.04;
    hankoGroup.rotation.z = wobble;
    hankoGroup.rotation.x = Math.cos(frame * 0.08) * 0.03;

    renderer.render(scene, camera);

    return () => {
      renderer.dispose();
      handleGeo.dispose();
      handleOutlineGeo.dispose();
      capGeo.dispose();
      baseGeo.dispose();
      groundGeo.dispose();
    };
  }, [frame, width, height, fps]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        backgroundColor: "#080a0f",
        overflow: "hidden",
        fontFamily: "'Courier New', monospace",
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 48,
          left: 64,
          borderLeft: "4px solid #ff1744",
          paddingLeft: 16,
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontSize: 28,
            fontWeight: 800,
            letterSpacing: "0.15em",
            color: "#ffffff",
            textTransform: "uppercase",
            textShadow: "0 2px 8px rgba(0,0,0,0.8)",
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.2em",
            color: "#00e5ff",
            marginTop: 4,
          }}
        >
          {subtitle} [PROCEDURAL THREE.JS ENGINE]
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 48,
          right: 64,
          fontSize: 14,
          color: "rgba(255, 255, 255, 0.4)",
          textAlign: "right",
          letterSpacing: "0.1em",
        }}
      >
        <div>FRAME: {String(frame).padStart(3, "0")} / 090</div>
        <div>ROTATION: {((frame / 90) * 360).toFixed(1)}°</div>
        <div>VRAM: ZERO (PROCEDURAL CPU)</div>
      </div>
    </div>
  );
};
