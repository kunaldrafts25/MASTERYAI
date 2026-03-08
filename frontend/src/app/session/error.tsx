"use client";

export default function SessionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="h-screen flex items-center justify-center bg-[#212121]">
      <div className="max-w-md text-center px-6">
        <div className="w-14 h-14 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">Session Error</h2>
        <p className="text-zinc-400 text-sm mb-6">
          {error.message || "The learning session encountered an error."}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition"
          >
            Retry
          </button>
          <a
            href="/session"
            className="px-5 py-2.5 border border-zinc-700 text-white text-sm font-medium rounded-lg hover:border-zinc-500 transition"
          >
            New Session
          </a>
        </div>
      </div>
    </div>
  );
}
