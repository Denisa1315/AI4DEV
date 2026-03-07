export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-gray-800/80 border border-gray-700/40 rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map(i => (
            <span key={i} className="typing-dot w-1.5 h-1.5 rounded-full bg-gray-500 block" />
          ))}
        </div>
      </div>
    </div>
  )
}