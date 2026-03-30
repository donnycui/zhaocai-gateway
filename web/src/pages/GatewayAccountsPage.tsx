export default function GatewayAccountsPage() {
  return (
    <section className="page">
      <div className="panel placeholder-panel">
        <div className="panel-header" style={{ marginBottom: 0 }}>
          <h3>Gateway 模块</h3>
          <p>这里会管理统一对外模型供给所需的上游账号、稳定别名、接入 key 和 failover 健康状态。</p>
        </div>
        <div className="placeholder-grid">
          <article className="placeholder-card">
            <strong>Upstream Accounts</strong>
            <span>接入公益站、官方站或代理站，并同步它们可用的真实模型。</span>
          </article>
          <article className="placeholder-card">
            <strong>Aliases</strong>
            <span>配置 `deep`、`signal/deep`、`draft/deep` 这类稳定别名，而不是让项目直接绑定真实模型名。</span>
          </article>
          <article className="placeholder-card">
            <strong>Failover</strong>
            <span>同一个别名下可挂多个 target，某个上游超时、5xx 或 429 时自动切换到备用站点。</span>
          </article>
          <article className="placeholder-card">
            <strong>Client Keys</strong>
            <span>给外部项目发统一接入 key，让它们只使用一个 `baseUrl + apiKey` 接入网关。</span>
          </article>
        </div>
      </div>
    </section>
  );
}
