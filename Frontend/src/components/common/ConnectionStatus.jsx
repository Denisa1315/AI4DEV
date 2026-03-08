import useAppStore from "../../store/useAppStore"

export default function ConnectionStatus({ connected }) {
  const wsConnected   = useAppStore((s) => s.wsConnected)
  const backendOnline = useAppStore((s) => s.backendOnline)

  // Allow prop override or fall back to store
  const isConnected = connected ?? wsConnected

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
      transition-all duration-500
      ${isConnected
        ? "bg-green-900/30 text-green-400 border border-green-800/50"
        : "bg-gray-800/60 text-gray-500 border border-gray-700/50"
      }`}>

      {/* Animated dot */}
      <span className="relative flex h-1.5 w-1.5">
        {isConnected && (
          <span className="animate-ping absolute inline-flex h-full w-full
            rounded-full bg-green-400 opacity-60" />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5
          ${isConnected ? "bg-green-400" : "bg-gray-600"}`} />
      </span>

      {isConnected ? "Live" : "Offline · Local Mode"}

      {/* Backend status dot — only shown when connected to show backend health */}
      {isConnected && !backendOnline && (
        <span className="text-yellow-500/70 text-xs border-l border-green-800/50 pl-2">
          Local AI
        </span>
      )}
    </div>
  )
}