import { useState } from "react"
import { Phone, X, Heart } from "lucide-react"

export default function CrisisAlert() {
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)" }}>
      <div className="crisis-ring bg-gray-900 border border-red-900/60 rounded-2xl p-6 max-w-sm w-full">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <Heart className="text-red-400" size={20} fill="#ef4444" />
            <span className="text-red-400 font-semibold text-sm">You're not alone</span>
          </div>
          <button onClick={() => setDismissed(true)} className="text-gray-600 hover:text-gray-400">
            <X size={18} />
          </button>
        </div>

        <p className="text-white text-base mb-2 leading-relaxed">
          I can see you might be going through something really difficult right now.
        </p>
        <p className="text-gray-400 text-sm mb-5 leading-relaxed">
          You don't have to face this alone. A trained counsellor is one call away.
        </p>

        <a href="tel:9152987821"
          className="flex items-center justify-center gap-2 w-full py-3 rounded-xl
            bg-red-600 hover:bg-red-500 text-white font-medium text-sm transition-colors mb-3">
          <Phone size={16} />
          iCall — 9152987821
        </a>

        <p className="text-center text-gray-600 text-xs">
          iCall · Mon–Sat · 8 AM – 10 PM · Free & confidential
        </p>

        <button onClick={() => setDismissed(true)}
          className="w-full mt-3 py-2.5 rounded-xl border border-gray-700 text-gray-400
            hover:text-gray-300 hover:border-gray-600 text-sm transition-colors">
          I'm safe, continue session
        </button>
      </div>
    </div>
  )
}