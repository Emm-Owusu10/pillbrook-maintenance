import { Link } from "react-router";

import HeroArt from "../HeroArt.jsx";

// What a signed-out visitor sees first.
export default function Landing() {
  return (
    <>
      <section className="hero" aria-labelledby="hero-heading">
        <div className="hero-inner">
          <div className="hero-text">
            <p className="eyebrow">Pill Brook Aquatics Ltd.</p>
            <h1 id="hero-heading">Report and track maintenance faults</h1>
            <p className="lead">
              Anyone on the farm will be able to report broken or faulty equipment here, with photos, and
              follow the repair until it is confirmed fixed.
            </p>
            <div className="cta-row">
              <Link className="cta cta-primary" to="/register">
                Create an account
              </Link>
              <Link className="cta cta-secondary" to="/login">
                Sign in
              </Link>
            </div>
            <p className="hero-note">
              You need the farm access code to create an account. Ask the Facility Manager.
            </p>
          </div>
          <HeroArt />
        </div>
        <svg className="wave" viewBox="0 0 1440 80" preserveAspectRatio="none" aria-hidden="true" focusable="false">
          <path d="M0 44 C 220 92 460 8 720 34 C 980 60 1220 92 1440 40 L1440 80 L0 80 Z" fill="#ffffff" />
        </svg>
      </section>

      <section className="how" aria-labelledby="how-heading">
        <h2 id="how-heading">How it works</h2>
        <ol className="step-list" role="list">
          <li>
            <h3>Report</h3>
            <p>Anyone on the farm can report broken equipment, with up to two photos, from a phone or a computer.</p>
          </li>
          <li>
            <h3>Track</h3>
            <p>The Facility Manager and the Administrator are told straight away and follow the repair until it is fixed.</p>
          </li>
          <li>
            <h3>Confirm</h3>
            <p>When the repair is done, the person who reported it confirms, or reopens the case if the problem is still there.</p>
          </li>
        </ol>
        <p className="how-note">
          Sign-in and accounts are ready now. Reporting, photos and tracking are being added step by step.
        </p>
      </section>
    </>
  );
}