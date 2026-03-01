"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) router.replace("/session");
  }, [router]);

  return (
    <>
    <nav className="border-b border-white/10 px-6 py-3 flex items-center justify-between">
      <Link href="/" className="text-lg font-semibold tracking-tight text-[#ececec]">MasteryAI</Link>
      <div className="flex gap-4 text-sm">
        <Link href="/login" className="text-zinc-400 hover:text-white transition-colors">Sign In</Link>
        <Link href="/register" className="text-white bg-zinc-800 px-3 py-1 rounded hover:bg-zinc-700 transition-colors">Sign Up</Link>
      </div>
    </nav>
    <div className="max-w-2xl mx-auto px-6 py-20 text-center">
      <h1 className="text-5xl font-bold mb-4">MasteryAI</h1>
      <p className="text-xl text-zinc-400 mb-4">
        AI-Powered Learning & Career Intelligence Platform
      </p>
      <p className="text-zinc-500 mb-12 max-w-lg mx-auto">
        Adaptive learning that validates real understanding through transfer
        tests, not memorization. Powered by multi-agent AI with real-time
        career readiness tracking.
      </p>

      <div className="flex gap-4 justify-center">
        <Link
          href="/register"
          className="px-8 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition"
        >
          Get Started
        </Link>
        <Link
          href="/login"
          className="px-8 py-3 border border-zinc-700 text-white font-medium rounded-lg hover:border-zinc-500 transition"
        >
          Sign In
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-6 mt-20 text-left">
        <div className="p-5 bg-[#2f2f2f]/60 rounded-lg border border-white/10">
          <h3 className="font-semibold mb-2">Transfer Testing</h3>
          <p className="text-sm text-zinc-400">
            Prove understanding by applying concepts in novel contexts, not just repeating examples.
          </p>
        </div>
        <div className="p-5 bg-[#2f2f2f]/60 rounded-lg border border-white/10">
          <h3 className="font-semibold mb-2">Multi-Agent AI</h3>
          <p className="text-sm text-zinc-400">
            5 specialized agents collaborate to teach, assess, and adapt your learning path.
          </p>
        </div>
        <div className="p-5 bg-[#2f2f2f]/60 rounded-lg border border-white/10">
          <h3 className="font-semibold mb-2">Career Intelligence</h3>
          <p className="text-sm text-zinc-400">
            Real-time career readiness scores tied to your actual mastery, not certificates.
          </p>
        </div>
      </div>
    </div>
    </>
  );
}
