"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { getLearnerState, updateProfile } from "@/lib/api";
import { NavBar } from "../providers";
import { ROUTES } from "@/lib/constants";

const EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"] as const;

function SettingsContent() {
  const { auth, logout } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [experience, setExperience] = useState("beginner");
  const [originalName, setOriginalName] = useState("");
  const [originalExperience, setOriginalExperience] = useState("beginner");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<{
    total_concepts_mastered: number;
    total_misconceptions_resolved: number;
    total_hours: number;
  } | null>(null);

  useEffect(() => {
    if (!auth.learnerId) return;
    getLearnerState(auth.learnerId)
      .then((data) => {
        const n = (data as { name?: string }).name || auth.name || "";
        const exp = (data as { learning_profile?: { experience_level?: string } })
          .learning_profile?.experience_level || (data as { experience_level?: string }).experience_level || "beginner";
        setName(n);
        setOriginalName(n);
        setExperience(exp);
        setOriginalExperience(exp);
        setStats((data as { stats?: typeof stats }).stats || null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [auth.learnerId, auth.name]);

  if (!auth.token) {
    router.push(ROUTES.LOGIN);
    return null;
  }

  const hasChanges = name !== originalName || experience !== originalExperience;

  async function handleSave() {
    if (!auth.learnerId || !hasChanges) return;
    setSaving(true);
    setMessage(null);
    try {
      const updates: { name?: string; experience_level?: string } = {};
      if (name !== originalName) updates.name = name;
      if (experience !== originalExperience) updates.experience_level = experience;
      const result = await updateProfile(auth.learnerId, updates);
      setOriginalName(result.name);
      setOriginalExperience(result.experience_level);
      setName(result.name);
      setExperience(result.experience_level);
      setMessage({ type: "success", text: "Profile updated" });
    } catch (e: unknown) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to save" });
    } finally {
      setSaving(false);
    }
  }

  function handleSignOut() {
    logout();
    router.push(ROUTES.LOGIN);
  }

  return (
    <>
      <NavBar />
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1">Settings</h1>
        <p className="text-zinc-400 mb-8">Manage your profile and preferences</p>

        {loading ? (
          <p className="text-zinc-400">Loading...</p>
        ) : (
          <div className="space-y-8">
            {/* Profile Section */}
            <section className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Profile</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Display Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    maxLength={100}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Experience Level</label>
                  <select
                    value={experience}
                    onChange={(e) => setExperience(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-zinc-500"
                  >
                    {EXPERIENCE_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {message && (
                <p className={`mt-4 text-sm ${message.type === "success" ? "text-green-400" : "text-red-400"}`}>
                  {message.text}
                </p>
              )}

              <button
                onClick={handleSave}
                disabled={!hasChanges || saving}
                className="mt-4 px-4 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </section>

            {/* Stats Section */}
            {stats && (
              <section className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Learning Stats</h2>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.total_concepts_mastered}</p>
                    <p className="text-sm text-zinc-400">Concepts Mastered</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.total_misconceptions_resolved}</p>
                    <p className="text-sm text-zinc-400">Misconceptions Fixed</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.total_hours.toFixed(1)}h</p>
                    <p className="text-sm text-zinc-400">Time Spent</p>
                  </div>
                </div>
              </section>
            )}

            {/* Account Section */}
            <section className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Account</h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">User ID</span>
                  <span className="text-zinc-300 font-mono text-xs">{auth.userId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Learner ID</span>
                  <span className="text-zinc-300 font-mono text-xs">{auth.learnerId}</span>
                </div>
              </div>
              <div className="mt-6 pt-4 border-t border-zinc-800">
                <button
                  onClick={handleSignOut}
                  className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm hover:bg-red-500/20 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<p className="text-zinc-400 p-8">Loading...</p>}>
      <SettingsContent />
    </Suspense>
  );
}
