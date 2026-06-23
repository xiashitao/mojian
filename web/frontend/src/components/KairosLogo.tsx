/** Kairos SVG logo mark — scales with font-size via em, adapts to currentColor. */
export function KairosLogo({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Kairos"
    >
      {/* Outer ring */}
      <circle cx="20" cy="20" r="16" stroke="currentColor" strokeWidth="1.25" />

      {/* Subtle tick marks at 3 / 6 / 9 o'clock */}
      <line x1="36" y1="20" x2="33" y2="20" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.4" />
      <line x1="4"  y1="20" x2="7"  y2="20" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.4" />
      <line x1="20" y1="36" x2="20" y2="33" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.4" />

      {/* Needle — from center to 12 o'clock */}
      <line x1="20" y1="20" x2="20" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />

      {/* Center pivot — solid dot */}
      <circle cx="20" cy="20" r="2.5" fill="currentColor" />

      {/* Accent mark at 12 o'clock */}
      <circle cx="20" cy="6" r="1.5" fill="currentColor" />
    </svg>
  );
}
