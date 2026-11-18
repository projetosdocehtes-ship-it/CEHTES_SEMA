import blocks from '../data/pop.json'
import './PopHelp.css'

const documentUrl = `${import.meta.env.BASE_URL}documentos/`
const textOf = block => block.runs?.map(run => run.text).join('') || ''

export default function PopHelp() {
  return <section className="workspace-card pop-help" role="tabpanel" aria-label="POP / Ajuda">
    <header className="pop-header">
      <div><h1>POP / Ajuda</h1><p>Consulte o procedimento operacional do simulador, passo a passo.</p></div>
      <a className="pop-download" href={`${documentUrl}POP_SIM_001_FV_BESS.docx`} download="POP_SIM_001_FV_BESS.docx">Baixar POP em Word</a>
    </header>
    <nav className="pop-index" aria-label="Seções do procedimento">
      <strong>Neste procedimento</strong>
      {blocks.map((block, index) => block.style === 'Heading 1'
        ? <a key={index} href={`#pop-section-${index}`}>{textOf(block)}</a> : null)}
    </nav>
    <article className="pop-document">
      {blocks.map((block, index) => {
        if (block.type === 'table') return <div className="pop-table-wrap" key={index}><table>
          <thead><tr>{block.rows[0].map((cell, i) => <th scope="col" key={i}>{cell}</th>)}</tr></thead>
          <tbody>{block.rows.slice(1).map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
        </table></div>
        if (block.type === 'image') return <img key={index} src={`${documentUrl}${block.src}`} alt={block.alt} loading="lazy" />
        const content = block.runs.map((run, i) => run.bold ? <strong key={i}>{run.text}</strong> : run.text)
        if (block.style === 'Heading 1') return <h2 id={`pop-section-${index}`} key={index}>{content}</h2>
        if (block.style === 'Heading 2') return <h3 key={index}>{content}</h3>
        if (block.style === 'Title') return <h2 className="pop-title" key={index}>{content}</h2>
        return <p key={index}>{content}</p>
      })}
    </article>
  </section>
}
