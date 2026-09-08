import Link from "next/link";

export default function Home() {
  return (
    <main id="main-content" className="product-shell">
      <header className="product-nav">
        <Link className="product-brand" href="/">
          RecallOps<span>MEMORY AUTHORITY</span>
        </Link>
        <nav>
          <Link href="/docs">Developers</Link>
          <Link href="/demo">Interactive demo</Link>
          <Link className="primary-button" href="/workspace">
            Open workspace ↗
          </Link>
        </nav>
      </header>
      <section className="product-hero">
        <div>
          <p className="eyebrow">POLICY MEMORY FOR AUTONOMOUS AGENTS</p>
          <h1>
            Your agent starts over.
            <br />
            <em>Its mistakes shouldn’t.</em>
          </h1>
          <p>
            Give every agent action a checkpoint. Recall past failures, check
            permissions and spending limits, and get a decision your code can
            enforce.
          </p>
          <div className="button-row">
            <Link className="primary-button" href="/workspace">
              Create your workspace →
            </Link>
            <Link className="secondary-button" href="/demo">
              Try the sample scenario
            </Link>
          </div>
          <small>Private workspace. Durable memory. No wallet required.</small>
        </div>
        <div className="product-proof">
          <div className="proof-caption">
            <span>THE NEXT ATTEMPT</span>
            <span>01 → 02</span>
          </div>
          <div className="proof-event">
            <span>Yesterday / Verification failed</span>
            <strong>Provider omitted required evidence.</strong>
            <code>dependency-audit:v1</code>
          </div>
          <div className="proof-memory">
            ↓ &nbsp; Retained in Sibyl Memory &nbsp; ↓
          </div>
          <div className="proof-event">
            <span>Today / Same provider, same task</span>
            <strong className="proof-deny">DENY</strong>
            <p>Past failure recalled before another attempt.</p>
          </div>
          <small>
            Illustrative flow ·{" "}
            <Link href="/demo">inspect the working demo</Link>
          </small>
        </div>
      </section>
      <section className="product-steps" aria-label="How RecallOps works">
        <article>
          <span>01 / DEFINE</span>
          <h2>Set the boundaries.</h2>
          <p>
            Choose allowed tasks, a per-action limit, a budget window, and
            providers your agent must avoid.
          </p>
        </article>
        <article>
          <span>02 / CHECK</span>
          <h2>Ask before acting.</h2>
          <p>
            Send a request with your agent key. Receive APPROVE, DENY, or
            ESCALATE with the memories behind the decision.
          </p>
        </article>
        <article>
          <span>03 / REMEMBER</span>
          <h2>Make failures useful.</h2>
          <p>
            Record a verified failure once. RecallOps checks it again across
            future requests and sessions.
          </p>
        </article>
      </section>
      <section className="product-callout">
        <div>
          <p className="eyebrow">BUILT TO BE INSPECTED</p>
          <h2>Every verdict comes with a reason.</h2>
          <p>
            Read the policy version, budget calculation, failure fingerprint,
            and durable evidence behind each decision.
          </p>
        </div>
        <Link href="/docs" className="secondary-button">
          Read the integration guide →
        </Link>
      </section>
      <footer className="product-footer">
        <span>RecallOps / Developer preview</span>
        <span>Decision gateway · Your application controls execution</span>
      </footer>
    </main>
  );
}
