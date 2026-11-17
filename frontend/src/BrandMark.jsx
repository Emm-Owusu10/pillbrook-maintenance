// A small logo mark in the brand colours: the sun and a fish. Decorative, so screen readers skip it.
export default function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <circle cx="17" cy="15" r="9" style={{ fill: "var(--accent)" }} />
      <path
        d="M6 30 C11 22 22 20 31 23 C34 24 36 26 38 27 L45 23 C46 27 46 33 45 37 L38 33 C36 35 34 37 31 38 C22 41 11 39 6 30 Z"
        fill="#ffffff"
      />
      <circle cx="12" cy="29" r="1.6" fill="#141444" />
    </svg>
  );
}