export default function Logo({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-label="AbidjanMob">
      <defs>
        <linearGradient id="amg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FF9A3C" />
          <stop offset="1" stopColor="#F06D00" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill="url(#amg)" />
      <path
        d="M14 46 C 26 46, 26 18, 40 18 h8"
        stroke="white"
        strokeWidth="5"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="49" cy="18" r="6" fill="white" />
      <circle cx="14" cy="46" r="4" fill="white" />
    </svg>
  )
}
