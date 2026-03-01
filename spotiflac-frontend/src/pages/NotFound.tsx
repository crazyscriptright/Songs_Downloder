import {
  IoHome,
  IoMusicalNotes,
  IoMusicalNotesOutline,
} from "react-icons/io5";
import { Link } from "react-router-dom";
import "@/styles/not-found.css";

const FLOATING_NOTES = [
  { left: "8%",  size: 22, dur: 9,  delay: 0 },
  { left: "18%", size: 14, dur: 13, delay: 2 },
  { left: "30%", size: 28, dur: 10, delay: 5 },
  { left: "44%", size: 16, dur: 14, delay: 1 },
  { left: "56%", size: 24, dur: 11, delay: 3.5 },
  { left: "67%", size: 18, dur: 12, delay: 6 },
  { left: "78%", size: 20, dur: 8,  delay: 0.5 },
  { left: "89%", size: 14, dur: 15, delay: 4 },
];

function VinylRecord() {
  return (
    <svg
      className="nf-vinyl"
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer disc */}
      <circle cx="100" cy="100" r="98" fill="var(--nf-vinyl-outer)" />
      {/* Grooves */}
      {[82, 72, 62, 52, 42, 35].map((r) => (
        <circle
          key={r}
          cx="100"
          cy="100"
          r={r}
          fill="none"
          stroke="var(--nf-vinyl-groove)"
          strokeWidth="1"
        />
      ))}
      {/* Label */}
      <circle cx="100" cy="100" r="30" fill="var(--nf-vinyl-label)" />
      {/* Label ring */}
      <circle
        cx="100"
        cy="100"
        r="29"
        fill="none"
        stroke="var(--nf-vinyl-label-border)"
        strokeWidth="1.5"
      />
      {/* Label text arc lines */}
      <line x1="78" y1="95" x2="122" y2="95" stroke="var(--nf-vinyl-label-border)" strokeWidth="1" opacity="0.5" />
      <line x1="78" y1="103" x2="122" y2="103" stroke="var(--nf-vinyl-label-border)" strokeWidth="0.7" opacity="0.35" />
      {/* Center hole */}
      <circle cx="100" cy="100" r="5" fill="var(--nf-vinyl-hole)" />
      {/* Outer rim */}
      <circle
        cx="100"
        cy="100"
        r="97"
        fill="none"
        stroke="var(--nf-vinyl-rim)"
        strokeWidth="2"
      />
    </svg>
  );
}

function NeedleArm() {
  return (
    <svg
      className="nf-needle"
      viewBox="0 0 60 100"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Pivot */}
      <circle cx="52" cy="8" r="6" fill="var(--nf-needle-color)" />
      <circle cx="52" cy="8" r="3" fill="var(--nf-needle-cap)" />
      {/* Arm */}
      <line
        x1="52"
        y1="8"
        x2="10"
        y2="90"
        stroke="var(--nf-needle-color)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {/* Cartridge */}
      <rect
        x="4"
        y="84"
        width="14"
        height="8"
        rx="2"
        fill="var(--nf-needle-color)"
      />
      {/* Stylus */}
      <line
        x1="11"
        y1="92"
        x2="11"
        y2="100"
        stroke="var(--nf-needle-cap)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function NotFound() {
  return (
    <div className="nf-wrapper">
      {/* Floating music notes background */}
      <div className="nf-notes-bg" aria-hidden="true">
        {FLOATING_NOTES.map((n, i) => (
          <span
            key={i}
            className="nf-note"
            style={{
              left: n.left,
              fontSize: n.size,
              animationDuration: `${n.dur}s`,
              animationDelay: `${n.delay}s`,
            }}
          >
            {i % 2 === 0 ? (
              <IoMusicalNotes size={n.size} />
            ) : (
              <IoMusicalNotesOutline size={n.size} />
            )}
          </span>
        ))}
      </div>

      <div className="nf-content">
        {/* Vinyl + needle */}
        <div className="nf-vinyl-scene">
          <div className="nf-vinyl-wrapper">
            <VinylRecord />
          </div>
          <NeedleArm />
        </div>

        {/* 404 */}
        <h1 className="nf-404">404</h1>

        {/* Title */}
        <h2 className="nf-title">Track Not Found</h2>

        {/* Divider */}
        <div className="nf-divider" />

        {/* Description */}
        <p className="nf-desc">
          Looks like this page skipped out of the playlist.
          <br />
          The URL might be wrong, or this page no longer exists.
        </p>

        {/* CTA */}
        <Link to="/" className="nf-btn">
          <IoHome size={18} />
          Back to Home
        </Link>
      </div>
    </div>
  );
}
