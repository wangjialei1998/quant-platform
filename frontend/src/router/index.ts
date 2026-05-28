import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import MarketDataCache from '@/views/market-data/MarketDataCache.vue'
import PortfolioCreate from '@/views/portfolios/PortfolioCreate.vue'
import PortfolioDetail from '@/views/portfolios/PortfolioDetail.vue'
import PortfolioList from '@/views/portfolios/PortfolioList.vue'
import SignalInsight from '@/views/signals/SignalInsight.vue'
import StrategyDetail from '@/views/strategies/StrategyDetail.vue'
import StrategyEditor from '@/views/strategies/StrategyEditor.vue'
import StrategyList from '@/views/strategies/StrategyList.vue'
import SystemSettings from '@/views/settings/SystemSettings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      redirect: '/portfolios',
      children: [
        { path: 'strategies', component: StrategyList },
        { path: 'strategies/new', component: StrategyEditor },
        { path: 'strategies/:id', component: StrategyDetail },
        { path: 'portfolios', component: PortfolioList },
        { path: 'portfolios/new', component: PortfolioCreate },
        { path: 'portfolios/:id', component: PortfolioDetail },
        { path: 'portfolios/:id/signals', component: SignalInsight },
        { path: 'market-data/cache', component: MarketDataCache },
        { path: 'settings', component: SystemSettings },
      ],
    },
  ],
})

export default router

