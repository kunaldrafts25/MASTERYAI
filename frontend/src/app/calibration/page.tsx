"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getCalibration } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { NavBar } from "../providers";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";

interface ConceptPoint {
  concept: string;
  confidence: number;
  mastery: number;
  gap: number;
}

function CalibrationContent() {
  const params = useSearchParams();
  const { auth } = useAuth();
  const learnerId = params.get("learner_id") || auth.learnerId;
  const [data, setData] = useState<{ overall_calibration: number; trend: string; per_concept: ConceptPoint[] } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!learnerId) return;
    getCalibration(learnerId)
      .then((d: any) => setData(d))
      .catch((e) => setError(e.message));
  }, [learnerId]);

  if (!learnerId) return <p className="text-zinc-400 p-8">No learner selected</p>;
  if (error) return <p className="text-red-400 p-8">{error}</p>;
  if (!data) return <p className="text-zinc-400 p-8">Loading...</p>;

  const points = data.per_concept.map((p) => ({
    ...p,
    fill: Math.abs(p.gap) < 0.15 ? "#22c55e" : Math.abs(p.gap) < 0.25 ? "#eab308" : "#ef4444",
  }));

  const overconfident = points.filter((p) => p.gap > 0.15);
  const underconfident = points.filter((p) => p.gap < -0.15);

  return (
    <>
    <NavBar />
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-1">Calibration Dashboard</h1>
      <p className="text-zinc-400 mb-6">How well does your confidence match your actual mastery?</p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <p className="text-zinc-400 text-sm">Overall Gap</p>
          <p className="text-2xl font-bold text-white">{(data.overall_calibration * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <p className="text-zinc-400 text-sm">Trend</p>
          <p className="text-2xl font-bold text-white capitalize">{data.trend}</p>
        </div>
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <p className="text-zinc-400 text-sm">Concepts Tracked</p>
          <p className="text-2xl font-bold text-white">{data.per_concept.length}</p>
        </div>
      </div>

      {points.length > 0 ? (
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800 mb-8">
          <h2 className="text-lg font-semibold text-white mb-4">Confidence vs Mastery</h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis type="number" dataKey="confidence" name="Confidence" domain={[0, 1]} stroke="#888" label={{ value: "Self-Reported Confidence", position: "bottom", fill: "#888" }} />
              <YAxis type="number" dataKey="mastery" name="Mastery" domain={[0, 1]} stroke="#888" label={{ value: "Actual Mastery", angle: -90, position: "left", fill: "#888" }} />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#666" strokeDasharray="5 5" />
              <Tooltip
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-zinc-800 border border-zinc-700 rounded p-2 text-sm">
                      <p className="text-white font-medium">{d.concept}</p>
                      <p className="text-zinc-400">Confidence: {(d.confidence * 100).toFixed(0)}%</p>
                      <p className="text-zinc-400">Mastery: {(d.mastery * 100).toFixed(0)}%</p>
                      <p className={d.gap > 0 ? "text-red-400" : d.gap < 0 ? "text-blue-400" : "text-green-400"}>
                        Gap: {(d.gap * 100).toFixed(1)}%
                      </p>
                    </div>
                  );
                }}
              />
              <Legend />
              <Scatter name="Concepts" data={points} fill="#8884d8" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-zinc-900 rounded-lg p-8 border border-zinc-800 mb-8 text-center text-zinc-400">
          Complete some learning sessions to see calibration data
        </div>
      )}

      {overconfident.length > 0 && (
        <div className="mb-6">
          <h3 className="text-base font-semibold text-red-400 mb-3">Overconfident Areas</h3>
          <div className="space-y-2">
            {overconfident.map((p) => (
              <div key={p.concept} className="flex justify-between bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2">
                <span className="text-white">{p.concept}</span>
                <span className="text-red-400">+{(p.gap * 100).toFixed(1)}% gap</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {underconfident.length > 0 && (
        <div>
          <h3 className="text-base font-semibold text-blue-400 mb-3">Underconfident Areas</h3>
          <div className="space-y-2">
            {underconfident.map((p) => (
              <div key={p.concept} className="flex justify-between bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2">
                <span className="text-white">{p.concept}</span>
                <span className="text-blue-400">{(p.gap * 100).toFixed(1)}% gap</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
    </>
  );
}

export default function CalibrationPage() {
  return (
    <Suspense fallback={<p className="text-zinc-400 p-8">Loading...</p>}>
      <CalibrationContent />
    </Suspense>
  );
}
