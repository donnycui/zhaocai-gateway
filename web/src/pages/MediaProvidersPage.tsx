export default function MediaProvidersPage() {
  return (
    <section className="page">
      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Media 模块</h3>
          <p>这里会管理 `zhaocai-media` 使用的独立供应商与模板，不与 OpenClaw 的普通文本模型主线混用。</p>
        </div>
        <div className="placeholder-grid">
          <article className="placeholder-card">
            <strong>Media Providers</strong>
            <span>维护图片、视频、TTS 等媒体能力所需的专用上游账号。</span>
          </article>
          <article className="placeholder-card">
            <strong>Media Templates</strong>
            <span>用声明式模板描述复杂媒体工作流，而不是把这些能力塞进普通 model 配置。</span>
          </article>
          <article className="placeholder-card">
            <strong>Catalog Export</strong>
            <span>后续会从这里导出 catalog，供 `zhaocai-media` 和网站消费。</span>
          </article>
        </div>
      </div>
    </section>
  );
}
