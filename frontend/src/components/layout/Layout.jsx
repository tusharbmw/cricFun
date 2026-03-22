import { Outlet } from 'react-router-dom'
import Header from './Header'
import BottomNav from './BottomNav'

export default function Layout() {
  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col">
      <Header />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-4 pb-20 md:pb-6">
        <Outlet />
      </main>
      <footer className="hidden md:block text-center text-xs text-gray-400 py-3 pb-5">
        TM, all rights reserved. By using this app you agree that Tushar is the Best!
      </footer>
      <BottomNav />
    </div>
  )
}
