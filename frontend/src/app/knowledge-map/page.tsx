"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import KnowledgeGraph from "@/components/KnowledgeGraph";
import { useAuth } from "@/lib/auth";
import { NavBar } from "../providers";

function KnowledgeMapContent() {
  const params = useSearchParams();
  const { auth } = useAuth();
  const learnerId = params.get("learner_id") || auth.learnerId || "";

  return (
    <>
    <NavBar />
    <div className="h-[calc(100vh-49px)] flex flex-col">
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Knowledge Map</h1>
      </div>
      <div className="flex-1 p-4">
        <KnowledgeGraph learnerId={learnerId || undefined} />
      </div>
    </div>
    </>
  );
}

export default function KnowledgeMapPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-zinc-500">Loading map...</div>}>
      <KnowledgeMapContent />
    </Suspense>
  );
}
