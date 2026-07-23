import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import '@/bones/registry'
import App from './App.tsx'
import HomeScreen from '@/modules/home/HomeScreen'
import { ModulePage } from '@/components/ModulePage'
import { FinanceModule, financeMeta } from '@/modules/finance/FinanceModule'
import { PortfolioModule, portfolioMeta } from '@/modules/portfolio/PortfolioModule'
import { WhatsappModule, whatsappMeta } from '@/modules/whatsapp/WhatsappModule'
import { DomainInsightsModule, domainInsightsMeta } from '@/modules/domain-insights/DomainInsightsModule'
import SettingsModule from '@/modules/settings/SettingsModule'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomeScreen />} />
          <Route
            path="finance"
            element={
              <ModulePage title={financeMeta.label} description={financeMeta.description} icon={financeMeta.icon}>
                <FinanceModule />
              </ModulePage>
            }
          />
          <Route
            path="portfolio"
            element={
              <ModulePage title={portfolioMeta.label} description={portfolioMeta.description} icon={portfolioMeta.icon}>
                <PortfolioModule />
              </ModulePage>
            }
          />
          <Route
            path="whatsapp"
            element={
              <ModulePage title={whatsappMeta.label} description={whatsappMeta.description} icon={whatsappMeta.icon}>
                <WhatsappModule />
              </ModulePage>
            }
          />
          <Route
            path="sports-data"
            element={
              <ModulePage title={domainInsightsMeta.label} description={domainInsightsMeta.description} icon={domainInsightsMeta.icon}>
                <DomainInsightsModule />
              </ModulePage>
            }
          />
          <Route path="settings" element={<SettingsModule />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
