import React from "react";
import { AbsoluteFill, Easing, interpolate } from "remotion";

/**
 * Motivated Vox Transitions: push_through, paper_slide, match_cut
 * Eliminates dead hard-cuts by providing tactile physical transitions
 * between Evidence Boards and internal beats.
 */
export const PushThroughTransitionOverlay: React.FC<{
  transitionOut: string;
  relFrame: number;
}> = ({ transitionOut, relFrame }) => {
  // 1. Push-Through (Camera plunges through focal document into new board)
  if (transitionOut === "push_through") {
    if (relFrame > 9) return null;
    const apertureScale = interpolate(relFrame, [0, 9], [0.25, 2.4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    const borderAlpha = interpolate(relFrame, [0, 2, 9], [0.85, 0.55, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 43,
          pointerEvents: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: "76%",
            height: "76%",
            border: `28px solid rgba(244, 238, 224, ${borderAlpha.toFixed(2)})`,
            boxShadow: `0 0 80px rgba(20, 14, 8, ${(borderAlpha * 0.85).toFixed(2)})`,
            transform: `scale(${apertureScale.toFixed(3)}) rotate(-1.5deg)`,
          }}
        />
      </AbsoluteFill>
    );
  }

  // 2. Paper Slide (New tabletop sheet slides across desk surface with drop shadow)
  if (transitionOut === "paper_slide") {
    if (relFrame > 8) return null;
    const slideX = interpolate(relFrame, [0, 8], [-110, 110], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.22, 1, 0.36, 1),
    });
    return (
      <AbsoluteFill
        style={{ zIndex: 44, pointerEvents: "none", overflow: "hidden" }}
      >
        <div
          style={{
            position: "absolute",
            top: "-6%",
            left: `${slideX.toFixed(1)}%`,
            width: "28%",
            height: "112%",
            backgroundColor: "#F5F0E4",
            borderLeft: "3px solid rgba(160, 130, 90, 0.55)",
            borderRight: "3px solid rgba(160, 130, 90, 0.55)",
            boxShadow:
              "-18px 0 36px rgba(25, 15, 5, 0.45), 18px 0 36px rgba(25, 15, 5, 0.45)",
            transform: "rotate(3.5deg)",
          }}
        />
      </AbsoluteFill>
    );
  }

  // 3. Match Cut (Tactile flash + red string snap across cut)
  if (transitionOut === "match_cut") {
    if (relFrame > 6) return null;
    const snapAlpha = interpolate(relFrame, [0, 1, 6], [0.55, 0.25, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 43,
          pointerEvents: "none",
          background: `radial-gradient(circle at 50% 50%, rgba(250, 246, 236, ${(snapAlpha * 0.45).toFixed(2)}) 0%, rgba(35, 22, 10, ${snapAlpha.toFixed(2)}) 100%)`,
        }}
      />
    );
  }

  return null;
};
