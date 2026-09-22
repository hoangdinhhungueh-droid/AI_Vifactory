export type CameraMove =
  | "static"
  | "slow_pan_left"
  | "slow_pan_right"
  | "slight_isometric_rotate"
  | "slow_push_in"
  | "slow_pull_out"
  | "cinematic_pan"
  | "macro_tilt";

export type TransitionOut = "hard_cut" | "stop_motion_flicker_cut" | "crossfade_short";

export interface Scene {
  scene_id: string;
  /** Path relative to Remotion's public/ dir, e.g. "assets/rendered/scene_01.mp4" */
  video_path: string;
  duration_seconds: number;
  /** Optional background audio/foley track, relative to public/. Silent if omitted. */
  audio_path?: string;
  /** Free-text description kept for reference; not rendered. */
  audio_cue?: string;
  text_overlay?: string | null;
  transition_out: TransitionOut;
  camera?: CameraMove;
}

export interface SceneMap {
  project_id: string;
  /** Optional global background music track, relative to public/, loops under all scenes. */
  background_music_path?: string;
  scenes: Scene[];
}

export type VoxelScene = Scene;
export type VoxelSceneMap = SceneMap;
