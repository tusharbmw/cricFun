import { create } from 'zustand'
import { tournamentsAPI } from '@/api/tournaments'

const STORAGE_KEY = 'currentTournamentId'

const useTournamentStore = create((set) => ({
  tournaments: [],
  currentTournament: null,
  isLoading: true,
  chooserOpen: false,

  init: async () => {
    try {
      const { data } = await tournamentsAPI.list()
      const savedId = parseInt(localStorage.getItem(STORAGE_KEY))
      const saved = data.find(t => t.id === savedId) ?? null
      const current = saved ?? (data.length === 1 ? data[0] : null)
      if (current) localStorage.setItem(STORAGE_KEY, String(current.id))
      set({ tournaments: data, currentTournament: current, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  setTournament: (tournament) => {
    localStorage.setItem(STORAGE_KEY, String(tournament.id))
    set({ currentTournament: tournament, chooserOpen: false })
  },

  openChooser:  () => set({ chooserOpen: true }),
  closeChooser: () => set({ chooserOpen: false }),
}))

export default useTournamentStore
