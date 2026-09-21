import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxBankCheckPayload {
  amount?: number | string;
  payee?: string;
  memo?: string;
  payer?: string;
  account_mask?: string;
  date?: string;
  check_number?: string;
}

export interface VoxBankCheckProps {
  title?: string;
  badge?: string;
  theme?: "vox_paper" | "noir_dossier" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;
  payload?: VoxBankCheckPayload;
  label?: string;
}

export const VoxBankCheck: React.FC<VoxBankCheckProps> = ({
  title,
  badge,
  theme = "vox_paper",
  layout = "full_bleed_focus",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 12fps stop-motion stepping
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  const checkSlide = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 140 },
  });

  const stampSlam = spring({
    frame: Math.max(0, frame - 18),
    fps,
    config: { damping: 8, mass: 0.4, stiffness: 220 },
  });

  // Animated dollar amount count-up
  const countProgress = interpolate(frame, [4, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (!payload || payload.amount === undefined || payload.amount === null) {
    return null;
  }

  const rawAmount = payload.amount;
  const numAmount = typeof rawAmount === "number" ? rawAmount : (parseFloat(String(rawAmount).replace(/[^0-9.]/g, "")) || 0);
  const currentCount = Math.round(numAmount * countProgress);
  const currencySymbol = (payload as any)?.currency || "$";
  const formattedCount = currencySymbol + currentCount.toLocaleString();

  const payee = payload?.payee || "DESIGNATED RECIPIENT ENTITY // NOMINEE";
  const payer = payload?.payer || "DISBURSEMENT AUTHORITY // TREASURY DIVISION";
  const memo = payload?.memo || "ALLOCATION DISBURSEMENT // TRANSACTION BATCH";
  const checkDate = payload?.date || "OFFICIAL AUDIT CYCLE";
  const checkNum = payload?.check_number || "NO. 008920";
  const displayBadge = badge || "FRAUDULENT DISBURSEMENT";

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 1040 : 620;

  return (
    <div
      style={{
        width,
        backgroundColor: "#f4f8f6", // Mint/security paper tint typical of official checks
        backgroundImage: "radial-gradient(#d1fae5 20%, transparent 20%)",
        backgroundSize: "12px 12px",
        borderRadius: 6,
        border: "2px solid #059669",
        padding: isFullBleed ? "28px 36px" : "20px 24px",
        boxShadow: "0 25px 60px rgba(0,0,0,0.75), 0 4px 12px rgba(0,0,0,0.3)",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        position: "relative",
        overflow: "hidden",
        transform: `scale(${checkSlide}) rotate(0.8deg)`,
        transformOrigin: "center center",
      }}
    >
      {/* Security Border Perforation Top */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 6,
          background: "repeating-linear-gradient(90deg, #059669 0, #059669 12px, transparent 12px, transparent 18px)",
        }}
      />

      {/* Check Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          borderBottom: "1px dashed #059669",
          paddingBottom: 10,
          marginBottom: 16,
        }}
      >
        <div>
          <div style={{ color: "#065f46", fontSize: isFullBleed ? 14 : 11, fontWeight: 800, letterSpacing: 1.5 }}>
            🏛️ {payer}
          </div>
          <div style={{ color: "#64748b", fontSize: 10, fontWeight: 700, marginTop: 2 }}>
            OFFICIAL GOVERNMENT DISBURSEMENT WARRANT
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ color: "#047857", fontSize: 12, fontWeight: 900, letterSpacing: 2 }}>
            {checkNum}
          </div>
          <div style={{ color: "#475569", fontSize: 11, fontWeight: 700, marginTop: 2 }}>
            DATE: {checkDate}
          </div>
        </div>
      </div>

      {/* Payee Line and Big Amount Box */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 20,
          margin: "12px 0",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ color: "#64748b", fontSize: 10, fontWeight: 800, letterSpacing: 1 }}>
            PAY TO THE ORDER OF:
          </div>
          <div
            style={{
              color: "#0f172a",
              fontSize: isFullBleed ? 18 : 14,
              fontWeight: 900,
              letterSpacing: 0.5,
              borderBottom: "1.5px solid #059669",
              paddingBottom: 4,
              marginTop: 4,
            }}
          >
            {payee}
          </div>
        </div>

        {/* Currency Amount Box */}
        <div
          style={{
            backgroundColor: "#ffffff",
            border: "2px solid #047857",
            borderRadius: 4,
            padding: isFullBleed ? "8px 24px" : "6px 16px",
            boxShadow: "inset 0 2px 4px rgba(0,0,0,0.1)",
            textAlign: "right",
          }}
        >
          <div style={{ color: "#059669", fontSize: 10, fontWeight: 800 }}>AMOUNT DISBURSED</div>
          <div
            style={{
              color: "#047857",
              fontSize: isFullBleed ? 32 : 24,
              fontWeight: 900,
              fontFamily: "'Courier New', Courier, monospace",
              letterSpacing: 1,
            }}
          >
            {formattedCount}
          </div>
        </div>
      </div>

      {/* Memo & Signature Line */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          marginTop: 18,
          paddingTop: 10,
          borderTop: "1px dashed #cbd5e1",
        }}
      >
        <div style={{ width: "55%" }}>
          <span style={{ color: "#64748b", fontSize: 10, fontWeight: 800 }}>MEMO / PROGRAM: </span>
          <span style={{ color: "#1e293b", fontSize: 12, fontWeight: 700 }}>{memo}</span>
        </div>

        <div style={{ textAlign: "center", width: "35%" }}>
          <div
            style={{
              borderBottom: "1.5px solid #334155",
              color: "#334155",
              fontSize: 16,
              fontFamily: "'Brush Script MT', cursive, sans-serif",
              fontStyle: "italic",
              paddingBottom: 2,
            }}
          >
            State Comptroller General
          </div>
          <div style={{ color: "#64748b", fontSize: 9, fontWeight: 700, marginTop: 3 }}>
            AUTHORIZED COMPLIANCE SIGNATURE
          </div>
        </div>
      </div>

      {/* Red Slam Stamp: FRAUDULENT CLAIM */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(${stampSlam}) rotate(-12deg)`,
          opacity: stampSlam > 0.05 ? 0.95 : 0,
          border: "4px solid #dc2626",
          borderRadius: 8,
          padding: "10px 28px",
          color: "#dc2626",
          fontSize: isFullBleed ? 34 : 24,
          fontWeight: 900,
          letterSpacing: 4,
          textTransform: "uppercase",
          backgroundColor: "rgba(255, 255, 255, 0.85)",
          boxShadow: "0 0 15px rgba(220, 38, 38, 0.4)",
          zIndex: 30,
          pointerEvents: "none",
        }}
      >
        {displayBadge}
      </div>
    </div>
  );
};
