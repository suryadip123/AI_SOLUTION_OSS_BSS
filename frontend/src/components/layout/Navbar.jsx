export default function Navbar() {
  return (
    <header className="bg-panel border-b border-slate-700 px-6 py-3 flex items-center justify-between">
      <span className="font-mono text-sm text-muted">AI Solution OSS-BSS · v1.0</span>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
        <span className="text-xs text-muted font-mono">Ollama Connected</span>
      </div>
    </header>
  )
}
