import { milestone } from "@/lib/milestone";

export default function Home() {
  return (
    <main>
      <section className="shell" aria-labelledby="product-title">
        <p className="eyebrow">Adaptive General Athleticism System</p>
        <h1 id="product-title">Build capability. Preserve the why.</h1>
        <p className="lede">
          AGAS now preserves delivered training and compatible reassessment as an immutable
          response, then reviews the original block hypothesis against explicit thresholds.
          Capability updates and next-block replanning remain deliberately deferred.
        </p>
        <dl className="status-card">
          <div>
            <dt>Current milestone</dt>
            <dd>{milestone.name}</dd>
          </div>
          <div>
            <dt>Available now</dt>
            <dd>{milestone.available}</dd>
          </div>
          <div>
            <dt>Deliberately deferred</dt>
            <dd>{milestone.deferred}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
