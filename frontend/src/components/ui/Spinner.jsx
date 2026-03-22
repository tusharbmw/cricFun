export default function Spinner({ className = '' }) {
  return (
    <div className={`flex justify-center py-10 ${className}`}>
      <span className="loading loading-spinner loading-md text-primary" />
    </div>
  )
}
