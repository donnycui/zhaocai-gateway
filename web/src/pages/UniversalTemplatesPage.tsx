export default function UniversalTemplatesPage() {
  return (
    <section className="page">
      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Universal 模板池</h3>
          <p>这里不会直接参与运行时，而是作为可复用的模板池，导入到 OpenClaw、Gateway 或 Media 后再各自独立管理。</p>
        </div>
        <div className="placeholder-grid">
          <article className="placeholder-card">
            <strong>Template Pool</strong>
            <span>维护常见供应商模板，减少重复录入。</span>
          </article>
          <article className="placeholder-card">
            <strong>Import to OpenClaw</strong>
            <span>导入后作为 OpenClaw 独立供应商使用，不与原模板联动。</span>
          </article>
          <article className="placeholder-card">
            <strong>Import to Gateway / Media</strong>
            <span>同一份模板可以派生到其他模块，但运行时始终保持各管各的。</span>
          </article>
        </div>
      </div>
    </section>
  );
}
