"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { useAuthStore } from "@/store/authStore";
import { signInWithPasskey } from "@/utils/passkeys";
import { homeRouteForUser } from "@/utils/homeRoute";

function getErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    if (error instanceof Error) return error.message;
    return "Unable to sign in.";
  }

  const data = error.response?.data;
  if (!data) return "Unable to connect to the server.";
  if (typeof data === "string") return data;
  if (typeof data === "object" && data !== null) {
    if ("detail" in data && typeof data.detail === "string") return data.detail;
    if ("error" in data) {
      const errorPayload = data.error;
      if (typeof errorPayload === "string") return errorPayload;
      if (typeof errorPayload === "object" && errorPayload !== null) {
        if ("message" in errorPayload && typeof errorPayload.message === "string") return errorPayload.message;
        if ("fields" in errorPayload && typeof errorPayload.fields === "object" && errorPayload.fields !== null) {
          const fields = errorPayload.fields as Record<string, unknown>;
          const message = fields.message;
          if (Array.isArray(message) && message.length > 0 && typeof message[0] === "string") {
            return message[0];
          }
        }
      }
    }
    return Object.values(data).flat().map(String).join(" ");
  }
  return "Login failed.";
}

function normalizeStringValue(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === "string") return value[0];
  return undefined;
}

function getOtpChallenge(error: unknown): { email?: string; challengeId?: string; message?: string } {
  if (!axios.isAxiosError(error)) return {};

  const data = error.response?.data;
  if (typeof data !== "object" || data === null) return {};

  const errorPayload = "error" in data ? data.error : undefined;
  if (typeof errorPayload !== "object" || errorPayload === null) return {};

  const fields = "fields" in errorPayload ? errorPayload.fields : undefined;
  if (typeof fields !== "object" || fields === null) return {};

  const fieldMap = fields as Record<string, unknown>;
  const email = normalizeStringValue(fieldMap.email);
  const challengeId = normalizeStringValue(fieldMap.challenge_id);
  const message = normalizeStringValue(fieldMap.message);

  return { email, challengeId, message };
}

export default function LoginClient() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const verifyOtp = useAuthStore((state) => state.verifyOtp);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [trustBrowser, setTrustBrowser] = useState(false);
  const [otpRequired, setOtpRequired] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpEmail, setOtpEmail] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchParams = useSearchParams();
  const inviteToken = searchParams.get("invite");

  async function handlePasskey() {
    if (!email.trim() || !password) {setError("Enter your email and password first, then use your administrator passkey.");return;}
    setLoading(true);setError(null);
    try {const user=await signInWithPasskey(email.trim().toLowerCase(),password,rememberMe);setPassword("");router.replace(homeRouteForUser(user));}
    catch(error){setError(getErrorMessage(error));}finally{setLoading(false);}
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!password) {
      setError("Password is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await login(
        {
          email: email.trim().toLowerCase(),
          password,
        },
        rememberMe,
      );

      if (result.status === "otp_required") {
        setOtpEmail(result.email);
        setChallengeId(result.challenge_id ?? "");
        setOtpRequired(true);
        setError(result.message || "OTP required. Check your email.");
        return;
      }

      if (inviteToken) {
        router.replace(`/invite?token=${encodeURIComponent(inviteToken)}`);
        return;
      }

      router.replace(homeRouteForUser(result.user));
    } catch (err) {
      const message = getErrorMessage(err);
      const challenge = getOtpChallenge(err);

      if (message.toLowerCase().includes("otp required") || challenge.message?.toLowerCase().includes("otp required")) {
        setOtpEmail((challenge.email || email.trim().toLowerCase()).trim());
        setChallengeId(challenge.challengeId ?? "");
        setOtpRequired(true);
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!otp.trim()) {
      setError("OTP is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const user = await verifyOtp(
        {
          challenge_id: challengeId,
          code: otp.trim(),
          trust_device: trustBrowser,
        },
        rememberMe,
      );

      if (inviteToken) {
        router.replace(`/invite?token=${encodeURIComponent(inviteToken)}`);
        return;
      }

      router.replace(homeRouteForUser(user));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-screen flex min-h-[calc(100vh-5rem)] items-center justify-center px-4 py-12">
      <div className="auth-card w-full max-w-md rounded-3xl border border-gray-200 bg-white p-6 shadow-xl sm:p-9">
        <div className="mb-8">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider auth-link">SmartBiz AI</p>
          <h1 className="text-3xl font-bold text-gray-950">Welcome back</h1>
          <p className="mt-2 text-sm text-gray-500">Sign in to manage your business workspace.</p>
        </div>

        {error && (
          <div role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {otpRequired ? (
          <form onSubmit={handleVerifyOtp} className="space-y-5">
            <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={trustBrowser} onChange={event => setTrustBrowser(event.target.checked)} /><span>Trust this browser for future sign-ins. Use this only on your own device.</span></label>
            <div>
              <label htmlFor="otp" className="mb-2 block text-sm font-medium text-gray-700">
                Verification code
              </label>
              <p className="mb-3 text-sm text-gray-500">
                Enter the code sent to {otpEmail}.
              </p>
              <input
                id="otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                disabled={loading}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-gray-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                placeholder="Enter your OTP"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-teal-700 px-4 py-3 font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {loading ? "Verifying..." : "Verify and sign in"}
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setOtpRequired(false);
                setTrustBrowser(false);
                setOtp("");
                setChallengeId("");
                setError(null);
              }}
              className="w-full text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              Use a different account
            </button>
          </form>
        ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="mb-2 block text-sm font-medium text-gray-700">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-gray-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="password" className="text-sm font-medium text-gray-700">Password</label>
              <Link href="/forgot-password" className="text-sm font-medium auth-link">
                Forgot password?
              </Link>
            </div>

            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 pr-16 text-gray-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                placeholder="Enter your password"
              />

              <button
                type="button"
                onClick={() => setShowPassword((c) => !c)}
                className="absolute inset-y-0 right-3 text-sm font-medium text-gray-500 hover:text-gray-800"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Remember me on this device
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-teal-700 px-4 py-3 font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <button type="button" disabled={loading} onClick={()=>void handlePasskey()} className="w-full rounded-lg border border-[var(--line)] px-4 py-3 font-semibold text-[var(--text)] disabled:opacity-50">Sign in with a passkey</button>
          <p className="text-sm text-[var(--muted)]">For platform administrators who have already added a passkey. Enter your password first. The regular Sign in button uses email verification.</p>
        </form>
        )}

        <p className="mt-7 text-center text-sm text-gray-600">
          New to SmartBiz AI?{" "}
          <Link href="/register" className="font-semibold auth-link">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
