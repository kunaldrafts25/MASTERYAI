export default function SessionLoading() {
  return (
    <div className="flex h-screen bg-[#212121]">
      {/* Sidebar skeleton */}
      <div className="hidden md:block w-64 bg-[#171717] border-r border-white/5 p-4">
        <div className="h-8 bg-zinc-800 rounded-lg animate-pulse mb-6" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-5 bg-zinc-800/60 rounded animate-pulse" />
          ))}
        </div>
      </div>
      {/* Chat skeleton */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="text-zinc-500 animate-pulse">Loading session...</div>
      </div>
    </div>
  );
}
