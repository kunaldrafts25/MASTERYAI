"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { registerUser } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Link from "next/link";


export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    experience_level: "beginner",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await registerUser(form);
      login(res.token, res.user_id, res.learner_id, res.name || form.name);
      router.push("/session");
    } catch (err: any) {
      if (err.message?.includes("409")) setError("Email already registered");
      else setError("Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
      <div className="w-full max-w-md p-8">
        <h1 className="text-3xl font-bold text-white mb-2 text-center">Create Account</h1>
        <p className="text-zinc-400 text-center mb-8">Start your personalized learning journey</p>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white focus:border-white focus:outline-none"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white focus:border-white focus:outline-none"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength={6}
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white focus:border-white focus:outline-none"
              placeholder="Min 6 characters"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Experience Level</label>
            <select
              value={form.experience_level}
              onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white focus:border-white focus:outline-none"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 disabled:opacity-50 transition"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="text-zinc-500 text-sm text-center mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-white hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
