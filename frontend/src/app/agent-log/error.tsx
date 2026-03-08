"use client";

export default function AgentLogError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#212121]">
      <div className="max-w-md text-center px-6">
        <h2 className="text-lg font-semibold text-white mb-2">Failed to load agent logs</h2>
        <p className="text-zinc-400 text-sm mb-6">{error.message}</p>
        <button
          onClick={reset}
          className="px-5 py-2.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
