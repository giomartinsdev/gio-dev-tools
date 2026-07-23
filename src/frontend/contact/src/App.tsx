import { useEffect, useRef, useState } from 'react'
import { useAuroraCanvas } from './hooks/useAuroraCanvas'
import { useMagneticName } from './hooks/useMagneticName'

function useClock() {
  const [time, setTime] = useState(() => formatTime())
  useEffect(() => {
    const id = setInterval(() => setTime(formatTime()), 15000)
    return () => clearInterval(id)
  }, [])
  return time
}

function formatTime() {
  return new Date().toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo',
  })
}

const CHIPS = ['Python', 'TypeScript', 'C# / .NET', 'DDD', 'AWS', 'FastAPI', 'React', 'PostgreSQL', 'Docker']

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const nameRef = useRef<HTMLHeadingElement>(null)
  const clock = useClock()

  useAuroraCanvas(canvasRef)
  useMagneticName(nameRef, stageRef)

  return (
    <div className="page">
      <div className="nav">
        <span className="mark">GM.</span>
        <span>Rio de Janeiro, {clock}</span>
      </div>

      <div className="stage" ref={stageRef}>
        <canvas id="field" ref={canvasRef} />

        <div className="stage-content">
          <div className="stage-name">
            <p className="eyebrow">Software Engineer</p>
            <h1 className="hero-name" ref={nameRef}>
              Giovanni<br /><em>Martins</em>
            </h1>
            <p className="hero-sub">
              Aprendo tecnologia porque amo aprender. Hoje isso significa pensar arquitetura pra
              um mundo AI-first.
            </p>
          </div>

          <div className="side-projects">
            <p className="eyebrow">Projetos</p>

            <a className="side-card" href="https://github.com/giomartinsdev/gio-dev-tools" target="_blank" rel="noopener">
              <div className="side-title">gio-dev-tools <span className="arrow">↗</span></div>
              <p className="side-desc">Ferramentas e automações pessoais, self-hosted.</p>
              <ul className="side-points">
                <li>Python + FastAPI, arquitetura DDD com CQRS</li>
                <li>Cotações B3 via Brapi · OCR de notas com Tesseract</li>
                <li>WhatsApp via Evolution API · RabbitMQ entre serviços</li>
                <li>Observabilidade com OpenTelemetry + Grafana/Loki</li>
                <li>Testes BDD (behave), cobertura mínima de 90% no CI</li>
              </ul>
              <div className="side-lang" style={{ '--dot': '#35E0C7' } as React.CSSProperties}>Python</div>
            </a>

            <a className="side-card" href="https://github.com/giomartinsdev/KRTBanking" target="_blank" rel="noopener">
              <div className="side-title">KRTBanking <span className="arrow">↗</span></div>
              <p className="side-desc">Sistema de gestão de limites PIX pra um banco fictício, com foco em Clean Architecture.</p>
              <ul className="side-points">
                <li>C# / .NET 8 · Clean Architecture com DDD</li>
                <li>Persistência em DynamoDB</li>
                <li>Logging estruturado + health checks</li>
                <li>4 suítes de teste por camada (domain, app, infra, API)</li>
              </ul>
              <div className="side-lang" style={{ '--dot': '#FF3E7F' } as React.CSSProperties}>C#</div>
            </a>
          </div>
        </div>
      </div>

      <div className="strip">
        <div className="strip-col">
          <p className="eyebrow" style={{ marginBottom: 8 }}>Sobre</p>
          <p>
            Curioso por natureza, gosto de entender como as coisas funcionam por dentro, não só de
            usar. Isso vira <strong>preocupação real com arquitetura</strong> (DDD, CQRS, sistemas
            que se sustentam sozinhos) e um jeito <strong>AI-first</strong> de trabalhar: agentes
            de IA fazem parte do meu fluxo todo dia, não são só autocomplete.
          </p>
          <div className="chip-row">
            {CHIPS.map((chip) => (
              <span key={chip} className="chip">{chip}</span>
            ))}
          </div>
        </div>

        <div className="strip-col">
          <p className="eyebrow" style={{ marginBottom: 8 }}>Contato</p>
          <div className="contact-list">
            <a className="contact-item" href="https://github.com/giomartinsdev" target="_blank" rel="noopener">
              GitHub <span className="go">↗</span>
            </a>
            <a className="contact-item" href="https://www.linkedin.com/in/giovannidealmeidamartins/" target="_blank" rel="noopener">
              LinkedIn <span className="go">↗</span>
            </a>
            <a className="contact-item" href="mailto:workwithgiomartinsdev@gmail.com">
              E-mail <span className="go">↗</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
