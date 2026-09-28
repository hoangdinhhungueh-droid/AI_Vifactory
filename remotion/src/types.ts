
export const CADENCE = {
  smooth: 30,
  fluid: 15,
  cutout: 10,
  archival: 6,
} as const;

export type CadenceKey = keyof typeof CADENCE;
export type KaraokeMode = 'full' | 'dim' | 'off';
export type CreditStyle = 'full' | 'tick' | 'none';

export type CameraMove =
  | "static"
  | "slow_pan_left"
  | "slow_pan_right"
  | "slight_isometric_rotate"
  | "slow_push_in"
  | "slow_pull_out"
  | "cinematic_pan"
  | "macro_tilt"
  | "snap_zoom"
  | "macro_orbit"
  | "cinematic_orbit"
  | "dolly_zoom"
  | "whip_zoom"
  | "focus_breathe_push"
  | "continuous_drift"
  | "seamless_whip_pan"
  | "handheld_shake";

export type TransitionOut =
  | "hard_cut"
  | "smash_cut"
  | "stop_motion_flicker_cut"
  | "crossfade_short"
  | "whip_pan"
  | "macro_zoom_through"
  | "ink_bleed"
  | "paper_tear"
  | "light_leak"
  | "circle_wipe";

export interface WordTimestamp {
  word: string;
  start_ms: number;
  end_ms: number;
  confidence?: number;
}

export interface VoxThresholdRatioPayload {
  baseline_value?: number; // e.g. 0.03
  detected_value?: number; // e.g. 0.72
  multiplier?: number; // e.g. 24
  unit?: string; // e.g. "g/kg"
  chemical_name?: string; // e.g. "二酸化硫黄" or "Sulfur Dioxide"
  standard_name?: string; // e.g. "基準値" or "Legal Standard"
  detected_name?: string; // e.g. "検出値" or "Detected Value"
  grid_cols?: number; // default 6
  grid_rows?: number; // default 4
  source_citation?: string; // e.g. "厚生労働省 検疫所検査結果 / 食品衛生法違反事例"
}

export interface VoxForensicOverlayData {
  type?:
    | "threshold_ratio"
    | "grid_ratio"
    | "ratio_grid"
    | "kinetic_counter"
    | "financial_chart"
    | "document_highlight"
    | "redacted_doc"
    | "paper_dossier"
    | "court_docket"
    | "redacted_memo"
    | "evidence_board"
    | "suspect_network"
    | "corporate_org_chart"
    | "bank_check"
    | "financial_ledger"
    | "tactical_map"
    | "radar_map"
    | "surveillance_crt"
    | "causal_flowchart"
    | "money_trail_network"
    | "evidence_3d_prop"
    | "3d_evidence_prop"
    | "kinetic_typography"
    | string;
  theme?: "noir_dossier" | "vox_paper" | "tech_infographic" | "surveillance_cctv" | "crimson_alert" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  title?: string;
  badge?: string;
  sfx_cue?: string;
  label?: string;
  payload?: any;
}

export interface VoxSourceCreditProps {
  source: string;
  verifiedDate?: string;
  docketNumber?: string;
  position?: "top_right" | "top_left" | "bottom_right" | "bottom_left";
  theme?: "noir" | "paper" | "tech";
  styleType?: "full" | "tick";
}

export interface VoxDisclosureBadgeProps {
  text?: string;
  subtext?: string;
  position?: "bottom_right" | "bottom_left" | "top_right" | "top_left";
  theme?: "dark" | "glass" | "minimal";
  isAiGenerated?: boolean;
}

export interface Scene {
  scene_id?: string;
  /** Path relative to Remotion's public/ dir or staticFile() or remote URL */
  video_path?: string;
  background?: string;
  foreground?: string;
  foregroundPosition?: "left" | "right" | "center";
  foregroundFadeFrames?: number;
  duration_seconds?: number;
  durationInFrames?: number;
  /** Optional background audio/foley track, relative to public/. Silent if omitted. */
  audio_path?: string;
  audio_cue?: string;
  foleysAudio?: string;
  foleys_audio?: string;
  text_overlay?: string | null;
  caption?: string;
  narration?: string;
  safeZone?: "top" | "bottom" | "top_left" | "top_right" | "bottom_left" | "bottom_right" | "none";
  statValue?: string;
  statLabel?: string;
  speakerTag?: string;
  actTitle?: string;
  card_segment_key?: string;
  cardSegmentKey?: string;
  subtitles?: WordTimestamp[];
  words?: WordTimestamp[];
  forensicOverlay?: VoxForensicOverlayData | string | null;
  forensic_overlay?: VoxForensicOverlayData | string | null;
  stampBadge?: string;
  stamp_badge?: string;
  cadence?: CadenceKey;
  karaokeMode?: KaraokeMode;
  karaoke_mode?: KaraokeMode;
  creditStyle?: CreditStyle;
  credit_style?: CreditStyle;
  sourceCredit?: string | VoxSourceCreditProps;
  source_credit?: string | VoxSourceCreditProps;
  disclosureBadge?: string | boolean;
  transition_out?: TransitionOut;
  transitionOut?: TransitionOut;
  camera?: {
    movement?: CameraMove;
    tension_level?: "low" | "medium" | "high";
  };
  cameraMovement?: CameraMove;
  tensionLevel?: "low" | "medium" | "high";
  opticalFx?: {
    vignette?: boolean;
    film_grain?: boolean;
    digital_glitch?: boolean;
    high_contrast?: boolean;
  };
}

export interface SceneMap {
  project_id: string;
  /** Optional global background music track, relative to public/, loops under all scenes. */
  background_music_path?: string;
  scenes: Scene[];
}

export type VoxelScene = Scene;
export type VoxelSceneMap = SceneMap;
