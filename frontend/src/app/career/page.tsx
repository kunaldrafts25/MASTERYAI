"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { getLearnerState, getReadiness } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { NavBar } from "../providers";

interface SkillBreakdown {
  skill_name: string;
  score: number;
  concepts_mastered: number;
  total_concepts: number;
}

interface Gap {
  skill_name: string;
  current_mastery: number;
  required_mastery: number;
  missing_concepts: string[];
  estimated_hours: number;
}

interface RoleReadiness {
  role_id: string;
  role_title: string;
  overall_score: number;
  skill_breakdown: SkillBreakdown[];
  gaps: Gap[];
  estimated_hours_to_ready: number;
  recommended_next: string | null;
}

interface RoleData {
  readiness: RoleReadiness;
  learning_path: any[];
  total_hours: number;
}

function barColor(score: number) {
  if (score > 0.7) return "bg-green-500";
  if (score > 0.3) return "bg-yellow-500";
  return "bg-red-500";
}

function CareerContent() {
  const params = useSearchParams();
  const { auth } = useAuth();
  const learnerId = params.get("learner_id") || auth.learnerId || "";

  const [roleData, setRoleData] = useState<Record<string, RoleData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!learnerId) return;
    doFetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learnerId]);

  async function doFetch() {
    setLoading(true);
    try {
      const state: any = await getLearnerState(learnerId);
      const careerTargets = state.career_targets || [];

      if (careerTargets.length === 0) {
        setRoleData({});
        setLoading(false);
        return;
      }

      const results: Record<string, RoleData> = {};
      for (const roleId of careerTargets) {
        try {
          const data: any = await getReadiness(learnerId, roleId);
          results[roleId] = data;
        } catch {
          // skip
        }
      }
      setRoleData(results);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  }

  if (!learnerId) {
    return (
      <div className="p-10 text-center text-zinc-500">
        <a href="/login" className="text-white underline">Sign in</a> to view career data.
      </div>
    );
  }

  if (loading) return <div className="p-10 text-center text-zinc-500">Loading career data...</div>;
  if (error) return <div className="p-10 text-center text-red-400">{error}</div>;

  const entries = Object.entries(roleData);

  return (
    <>
    <NavBar />
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Career Dashboard</h1>

      {entries.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-emerald-600/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl text-emerald-400">P</span>
          </div>
          <h2 className="text-lg font-medium text-zinc-300 mb-2">No career goals set yet</h2>
          <p className="text-zinc-500 max-w-md mx-auto mb-6">
            Tell your professor what career you&apos;re aiming for during a learning session,
            and your readiness dashboard will appear here.
          </p>
          <a
            href="/session"
            className="inline-block px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors text-sm font-medium"
          >
            Start a session
          </a>
        </div>
      )}

      <div className="space-y-8">
        {entries.map(([roleId, data]) => {
          const r = data.readiness;
          const overallPct = Math.round(r.overall_score * 100);

          return (
            <div key={roleId} className="border border-white/10 rounded-lg p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">{r.role_title || roleId}</h2>
                <span className="text-sm text-zinc-400">{overallPct}% ready</span>
              </div>

              <div className="w-full h-2 bg-zinc-800 rounded-full mb-5">
                <div
                  className={`h-full rounded-full transition-all ${barColor(r.overall_score)}`}
                  style={{ width: `${overallPct}%` }}
                />
              </div>

              {r.skill_breakdown.length > 0 && (
                <div className="space-y-3 mb-5">
                  <h3 className="text-sm text-zinc-400 font-medium">Skills</h3>
                  {r.skill_breakdown.map((skill, i) => (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-zinc-300">{skill.skill_name}</span>
                        <span className="text-zinc-500">
                          {Math.round(skill.score * 100)}% ({skill.concepts_mastered}/{skill.total_concepts})
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-zinc-800 rounded-full">
                        <div
                          className={`h-full rounded-full ${barColor(skill.score)}`}
                          style={{ width: `${Math.round(skill.score * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {r.gaps.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm text-zinc-400 font-medium mb-2">Top Gaps</h3>
                  <div className="space-y-1.5">
                    {r.gaps.slice(0, 5).map((gap, i) => (
                      <div key={i} className="flex justify-between text-sm bg-zinc-900/50 rounded px-3 py-1.5">
                        <span className="text-zinc-300">{gap.skill_name}</span>
                        <span className="text-zinc-500">~{gap.estimated_hours.toFixed(1)}h to close</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between text-xs text-zinc-500 pt-3 border-t border-white/5">
                {r.recommended_next && (
                  <span>Next: <span className="text-zinc-300">{r.recommended_next}</span></span>
                )}
                <span>Est. {data.total_hours.toFixed(1)}h to ready</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
    </>
  );
}

export default function CareerPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-zinc-500">Loading...</div>}>
      <CareerContent />
    </Suspense>
  );
}
