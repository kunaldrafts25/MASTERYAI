export default function KnowledgeMapLoading() {
  return (
    <div className="min-h-screen bg-[#212121]">
      <div className="border-b border-white/10 px-6 py-3">
        <div className="h-6 w-24 bg-zinc-800 rounded animate-pulse" />
      </div>
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse mb-6" />
        <div className="h-[600px] bg-zinc-900 rounded-lg animate-pulse flex items-center justify-center">
          <div className="text-zinc-600">Loading knowledge graph...</div>
        </div>
      </div>
    </div>
  );
}
