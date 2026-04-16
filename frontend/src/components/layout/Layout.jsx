import { Outlet } from 'react-router-dom'
import Header from './Header'
import BottomNav from './BottomNav'
import useAuthStore from '@/store/authStore'

export default function Layout() {
  const { user } = useAuthStore()
  const isPending = user && user.is_approved === false

  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col">
      <Header />
      {isPending && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 text-center text-sm text-amber-800">
          Your account is <strong>pending approval</strong>. You can explore and make picks, but you won't appear on the leaderboard until an admin approves you.
        </div>
      )}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-4 pb-20 md:pb-6">
        <Outlet />
      </main>
      <footer className="text-center text-xs text-gray-400 py-3 pb-20 md:pb-5">
        TM, all rights reserved. By using this app you agree that Tushar is the Best!
      </footer>
      <BottomNav />
    </div>
  )
}
