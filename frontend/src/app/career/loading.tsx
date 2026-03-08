export default function CareerLoading() {
  return (
    <div className="min-h-screen bg-[#212121]">
      <div className="border-b border-white/10 px-6 py-3">
        <div className="h-6 w-24 bg-zinc-800 rounded animate-pulse" />
      </div>
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse mb-6" />
        <div className="space-y-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="border border-white/10 rounded-lg p-5">
              <div className="flex justify-between mb-4">
                <div className="h-6 w-40 bg-zinc-800 rounded animate-pulse" />
                <div className="h-5 w-20 bg-zinc-800 rounded animate-pulse" />
              </div>
              <div className="h-2 bg-zinc-800 rounded-full mb-5 animate-pulse" />
              <div className="space-y-3">
                {[...Array(3)].map((_, j) => (
                  <div key={j}>
                    <div className="h-4 w-32 bg-zinc-800/60 rounded animate-pulse mb-1" />
                    <div className="h-1.5 bg-zinc-800 rounded-full animate-pulse" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
