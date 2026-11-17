// Decorative artwork for the landing page: the logo's sun and two fish. Screen readers skip it.
const BIG_FISH =
  "M70 200 C108 140 212 118 300 138 C330 146 355 160 372 172 L452 134 C464 168 464 218 452 252 L372 222 C355 236 330 250 300 258 C212 278 108 262 70 200 Z";
const DORSAL_FIN = "M190 140 C206 100 250 88 292 100 C272 112 252 126 236 140 Z";

export default function HeroArt() {
  return (
    <svg className="hero-art" viewBox="0 0 520 340" aria-hidden="true" focusable="false">
      <circle cx="150" cy="98" r="70" style={{ fill: "var(--accent)" }} />
      <g fill="#eaf1ff">
        <path d={BIG_FISH} />
        <path d={DORSAL_FIN} />
        <path d="M205 262 C218 290 242 300 266 296 C254 282 248 270 246 262 Z" />
      </g>
      <path d="M150 212 C176 196 216 196 246 200 C226 222 192 234 166 232 Z" fill="#141444" opacity="0.3" />
      <circle cx="112" cy="190" r="7" fill="#141444" />
      <g transform="translate(40 222) scale(0.36)" fill="#bfd0f5">
        <path d={BIG_FISH} />
        <path d={DORSAL_FIN} />
        <circle cx="112" cy="190" r="9" fill="#141444" />
      </g>
    </svg>
  );
}