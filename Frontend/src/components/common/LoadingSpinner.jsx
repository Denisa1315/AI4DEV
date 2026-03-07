export default function LoadingSpinner({ size = "md", color = "#60A5FA", label }) {
  const dimensions = { sm: 16, md: 24, lg: 36, xl: 48 }
  const s = dimensions[size] || 24
  const stroke = size === "sm" ? 2 : 2.5

  return (
    <span className="inline-flex flex-col items-center justify-center gap-2">
      <svg
        width={s}
        height={s}
        viewBox="0 0 24 24"
        fill="none"
        style={{ animation: "spinner-rotate 0.9s linear infinite" }}
      >
        <style>{`
          @keyframes spinner-rotate {
            from { transform: rotate(0deg);   }
            to   { transform: rotate(360deg); }
          }
          @keyframes spinner-dash {
            0%   { stroke-dasharray: 1, 150;  stroke-dashoffset: 0;   }
            50%  { stroke-dasharray: 90, 150; stroke-dashoffset: -35; }
            100% { stroke-dasharray: 90, 150; stroke-dashoffset: -124;}
          }
        `}</style>

        {/* Track */}
        <circle
          cx="12" cy="12" r="10"
          stroke={color}
          strokeWidth={stroke}
          strokeOpacity="0.15"
          fill="none"
        />

        {/* Spinning arc */}
        <circle
          cx="12" cy="12" r="10"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          style={{
            animation: "spinner-dash 1.4s ease-in-out infinite",
            transformOrigin: "center",
          }}
        />
      </svg>

      {label && (
        <span className="text-xs" style={{ color }}>
          {label}
        </span>
      )}
    </span>
  )
}