export default function CalibrationLoading() {
  return (
    <div className="min-h-screen bg-[#212121]">
      <div className="border-b border-white/10 px-6 py-3">
        <div className="h-6 w-24 bg-zinc-800 rounded animate-pulse" />
      </div>
      <div className="p-6 max-w-5xl mx-auto">
        <div className="h-8 w-56 bg-zinc-800 rounded animate-pulse mb-2" />
        <div className="h-5 w-80 bg-zinc-800/60 rounded animate-pulse mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
              <div className="h-4 w-20 bg-zinc-800 rounded animate-pulse mb-2" />
              <div className="h-8 w-16 bg-zinc-800 rounded animate-pulse" />
            </div>
          ))}
        </div>
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800 h-[400px] animate-pulse flex items-center justify-center">
          <div className="text-zinc-600">Loading chart...</div>
        </div>
      </div>
    </div>
  );
}
