import type { SVGProps } from "react";

type KairosLogoProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

/** Kairos logo mark: an abstract time gate with a fixed point of decision. */
export function KairosLogo({ size = 40, className = "", ...svgProps }: KairosLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Kairos"
      {...svgProps}
    >
      <path
        d="M20 4.75C29.2 4.75 35.25 10.8 35.25 20S29.2 35.25 20 35.25 4.75 29.2 4.75 20 10.8 4.75 20 4.75Z"
        stroke="currentColor"
        strokeWidth="1.15"
        strokeOpacity="0.32"
      />
      <path
        d="M12.15 20C14.95 15.6 17.6 13.45 20 13.45S25.05 15.6 27.85 20C25.05 24.4 22.4 26.55 20 26.55S14.95 24.4 12.15 20Z"
        fill="var(--cinnabar-soft, rgba(198, 77, 63, 0.12))"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeOpacity="0.72"
        strokeLinejoin="round"
      />
      <path
        d="M14.1 29.15C17.05 26.2 18.2 22.4 18.2 15.55V9.25"
        stroke="currentColor"
        strokeWidth="1.45"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M25.9 10.85C22.95 13.8 21.8 17.6 21.8 24.45v6.3"
        stroke="currentColor"
        strokeWidth="1.45"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M20 9.25v21.5"
        stroke="currentColor"
        strokeWidth="1.05"
        strokeLinecap="round"
        strokeOpacity="0.48"
      />
      <circle
        cx="20"
        cy="20"
        r="3.05"
        fill="var(--cinnabar, currentColor)"
      />
      <circle cx="20" cy="20" r="1.05" fill="var(--bone-100, #fff)" fillOpacity="0.82" />
    </svg>
  );
}
