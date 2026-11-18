export default function SimulationPanel({ simulacao }) {
  return (
    <section className="simulation-panel">
      <h3>Resultado da simulação</h3>

      {!simulacao ? (
        <p className="muted">Nenhuma simulação executada.</p>
      ) : (
        <>
          <div className="simulation-grid">
            <div className="info-card">
              <span>Status</span>
              <strong>{simulacao.status}</strong>
            </div>
            <div className="info-card">
              <span>Nós</span>
              <strong>{simulacao.resumo?.quantidade_nos ?? 0}</strong>
            </div>
            <div className="info-card">
              <span>Ligações</span>
              <strong>{simulacao.resumo?.quantidade_ligacoes ?? 0}</strong>
            </div>
            <div className="info-card">
              <span>Potência total</span>
              <strong>{simulacao.resumo?.potencia_total_kw ?? 0} kW</strong>
            </div>
            <div className="info-card">
              <span>Energia total</span>
              <strong>{simulacao.resumo?.energia_total_kwh ?? 0} kWh</strong>
            </div>
          </div>

          <div className="alerts-box">
            <h4>Alertas</h4>
            {simulacao.alertas?.length ? (
              <ul>
                {simulacao.alertas.map((alerta, index) => (
                  <li key={index}>{alerta}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">Sem alertas.</p>
            )}
          </div>
        </>
      )}
    </section>
  )
}
