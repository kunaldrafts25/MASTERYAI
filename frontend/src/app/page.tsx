"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ROUTES, APP_NAME, APP_TAGLINE, LANDING_FEATURES } from "@/lib/constants";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) router.replace(ROUTES.SESSION);
  }, [router]);

  return (
    <>
    <nav className="border-b border-white/10 px-6 py-3 flex items-center justify-between">
      <Link href={ROUTES.HOME} className="text-lg font-semibold tracking-tight text-foreground">{APP_NAME}</Link>
      <div className="flex gap-4 text-sm">
        <Link href={ROUTES.LOGIN} className="text-zinc-400 hover:text-white transition-colors">Sign In</Link>
        <Link href={ROUTES.REGISTER} className="text-white bg-zinc-800 px-3 py-1 rounded hover:bg-zinc-700 transition-colors">Sign Up</Link>
      </div>
    </nav>
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12 sm:py-20 text-center">
      <h1 className="text-3xl sm:text-5xl font-bold mb-4">{APP_NAME}</h1>
      <p className="text-xl text-zinc-400 mb-4">
        {APP_TAGLINE}
      </p>
      <p className="text-zinc-500 mb-12 max-w-lg mx-auto">
        Adaptive learning that validates real understanding through transfer
        tests, not memorization. Powered by multi-agent AI with real-time
        career readiness tracking.
      </p>

      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Link
          href={ROUTES.REGISTER}
          className="px-8 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition"
        >
          Get Started
        </Link>
        <Link
          href={ROUTES.LOGIN}
          className="px-8 py-3 border border-zinc-700 text-white font-medium rounded-lg hover:border-zinc-500 transition"
        >
          Sign In
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mt-12 sm:mt-20 text-left">
        {LANDING_FEATURES.map((feature) => (
          <div key={feature.title} className="p-5 bg-input-bg/60 rounded-lg border border-white/10">
            <h3 className="font-semibold mb-2">{feature.title}</h3>
            <p className="text-sm text-zinc-400">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </div>
    </>
  );
}
