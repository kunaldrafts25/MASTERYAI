"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import dynamic from "next/dynamic";
import { useAuth } from "@/lib/auth";
import { NavBar } from "../providers";

const KnowledgeGraph = dynamic(() => import("@/components/KnowledgeGraph"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[400px] md:h-[600px] bg-gray-900 rounded-lg">
      <p className="text-gray-400 animate-pulse">Loading knowledge graph...</p>
    </div>
  ),
});

function KnowledgeMapContent() {
  const params = useSearchParams();
  const { auth } = useAuth();
  const learnerId = params.get("learner_id") || auth.learnerId || "";

  return (
    <>
    <NavBar />
    <div className="h-[calc(100vh-49px)] flex flex-col">
      <div className="px-4 md:px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Knowledge Map</h1>
      </div>
      <div className="flex-1 p-3 md:p-4">
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
