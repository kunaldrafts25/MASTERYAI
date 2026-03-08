export default function AgentLogLoading() {
  return (
    <div className="min-h-screen bg-[#212121]">
      <div className="border-b border-white/10 px-6 py-3">
        <div className="h-6 w-24 bg-zinc-800 rounded animate-pulse" />
      </div>
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="h-8 w-36 bg-zinc-800 rounded animate-pulse mb-6" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="h-5 w-20 bg-zinc-800 rounded-full animate-pulse" />
                <div className="h-4 w-32 bg-zinc-800/60 rounded animate-pulse" />
              </div>
              <div className="h-4 w-full bg-zinc-800/40 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
