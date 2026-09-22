import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Video,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { Scene, SceneMap } from "../types";

/** Tổng số frame của toàn bộ video, dùng cho Composition.durationInFrames */
export function calculateTotalFrames(sceneMap: SceneMap, fps: number): number {
  if (!sceneMap || !sceneMap.scenes || sceneMap.scenes.length === 0) return 300;
  return sceneMap.scenes.reduce(
    (total, scene) => total + Math.max(1, Math.round((scene.duration_seconds || 5) * fps)),
    0
  );
}

export const VoxelStopMotionVideo: React.FC<{ sceneMap?: SceneMap }> = ({
  sceneMap,
}) => {
  const fps = 30;
  let frameCursor = 0;
  const scenes = sceneMap?.scenes || [];

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((scene, index) => {
        const durationInFrames = Math.max(1, Math.round((scene.duration_seconds || 5) * fps));
        const from = frameCursor;
        frameCursor += durationInFrames;

        return (
          <Sequence
            key={scene.scene_id || `voxel-sc-${index}`}
            from={from}
            durationInFrames={durationInFrames}
            name={scene.scene_id || `scene-${index + 1}`}
          >
            <SceneLayer
              scene={scene}
              durationInFrames={durationInFrames}
              isLast={index === scenes.length - 1}
            />
          </Sequence>
        );
      })}

      {sceneMap?.background_music_path && (
        <Audio src={staticFile(sceneMap.background_music_path)} volume={0.4} />
      )}
    </AbsoluteFill>
  );
};

const SceneLayer: React.FC<{
  scene: Scene;
  durationInFrames: number;
  isLast: boolean;
}> = ({ scene, durationInFrames, isLast }) => {
  const frame = useCurrentFrame();

  // --- Transition xử lý theo transition_out của scene:
  // Áp dụng hiệu ứng vào phần đầu của scene hiện tại (entrance).
  let opacity = 1;

  if (scene.transition_out === "stop_motion_flicker_cut") {
    // Nhấp nháy 2-3 frame ở đầu scene để giả cảm giác "đổi khung hình"
    // đặc trưng stop-motion, thay vì fade mượt.
    opacity = interpolate(
      frame,
      [0, 1, 2, 3, 4],
      [0, 1, 0.3, 1, 1],
      { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
    );
  } else if (scene.transition_out === "crossfade_short") {
    // Fade in ngắn (6 frame ~0.2s)
    opacity = interpolate(frame, [0, 6], [0, 1], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
  }

  // Fade out nhẹ ở cuối video (scene cuối cùng)
  if (isLast) {
    const fadeOutStart = Math.max(0, durationInFrames - 15);
    opacity = Math.min(
      opacity,
      interpolate(frame, [fadeOutStart, durationInFrames], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    );
  }

  return (
    <AbsoluteFill style={{ opacity }}>
      {scene.video_path && (
        <Video
          src={staticFile(scene.video_path)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      )}

      {scene.audio_path && (
        <Audio src={staticFile(scene.audio_path)} volume={1} />
      )}

      {scene.text_overlay && <TextOverlay text={scene.text_overlay} />}
    </AbsoluteFill>
  );
};

const TextOverlay: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 80,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          fontFamily: "'Segoe UI', Roboto, sans-serif",
          fontSize: 48,
          fontWeight: 800,
          color: "white",
          textShadow: "0 2px 10px rgba(0,0,0,0.85)",
          background: "rgba(15, 23, 42, 0.85)",
          border: "2px solid rgba(242, 166, 59, 0.5)",
          padding: "12px 32px",
          borderRadius: 12,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
