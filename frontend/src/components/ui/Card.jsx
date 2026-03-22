export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-white border border-gray-100 rounded-xl shadow-sm ${className}`}>
      <div className="card-body p-4">{children}</div>
    </div>
  )
}
