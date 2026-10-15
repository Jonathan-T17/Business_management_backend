"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, ArrowRight, LockKeyhole } from "lucide-react";
import { companySetupApi } from "@/api/companySetupApi";
import { useAuthStore } from "@/store/authStore";
import { normalizeApiError } from "@/utils/apiError";
import { Button } from "@/components/ui/Button";
import { SetupEditingProvider, useSetupEditing } from "./SetupEditingContext";
import { SetupSavedChoices } from "./SetupSavedChoices";
import HeadquartersWorkspace from "./HeadquartersWorkspace";
import CompanyProfileSection from "./CompanyProfileSection";
import SetupFormsWorkspace from "./SetupFormsWorkspace";
import DepartmentsPage from "@/app/(dashboard)/departments/page";
import TeamsPage from "@/app/(dashboard)/teams/page";
import PositionsPage from "@/app/(dashboard)/employees/positions/page";
import AccessPage from "@/app/(dashboard)/settings/roles-permissions/page";
import InvitationsPage from "@/app/(dashboard)/employees/invite/page";

const stages = [
  { code: "company", title: "Company profile", description: "Save your company identity, country, timezone and currency." },
  { code: "organization", title: "Headquarters and branches", description: "Choose your one headquarters. Add other branches only if your company needs them." },
  { code: "departments", title: "Departments and teams", description: "Organise work within your locations. Departments and teams are optional for a small company." },
  { code: "positions", title: "Positions and reporting lines", description: "Choose where each position belongs and who it reports to. You will review its access in the next step." },
  { code: "permissions", title: "Position responsibilities and access", description: "Choose a position, review what it can do, and save its permissions before inviting people." },
  { code: "forms", title: "Choose and adapt forms", description: "Start with a template, adjust it for your company, then preview and publish. Published forms are available to eligible employees." },
  { code: "employees", title: "Invite your people", description: "Invite employees to the structure you prepared. You can assign their positions after they join." },
  { code: "finish", title: "Review and activate", description: "Check your saved choices and open your company workspace." },
];
const stepUrl = (code: string) => "/settings/onboarding?step=" + code;

function SetupJourneyContent({ compact = false }: { compact?: boolean }) {
  const user = useAuthStore(state => state.user);
  const router = useRouter();
  const params = useSearchParams();
  const cache = useQueryClient();
  const setupEditing = useSetupEditing();
  const [navigationNotice, setNavigationNotice] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [structurePart, setStructurePart] = useState("departments");
  const query = useQuery({ queryKey: ["company-setup", "onboarding-status", user?.id], queryFn: companySetupApi.status, retry: false });
  const review = useMutation({ mutationFn: companySetupApi.completeStep, onSuccess: async (_, code) => {
    await cache.invalidateQueries({ queryKey: ["company-setup"] });
    setEditing(null);
    router.push(stepUrl(stages[Math.min(stages.findIndex(step => step.code === code) + 1, stages.length - 1)].code));
  } });
  const finish = useMutation({ mutationFn: companySetupApi.finish, onSuccess: async () => { await cache.invalidateQueries({ queryKey: ["company-setup"] }); router.push("/dashboard"); } });
  if (query.isPending) return <p role="status">Loading your company setup…</p>;
  if (query.isError) return <div role="alert" className="rounded-xl border p-6"><p>We could not load setup progress.</p><Button onClick={() => query.refetch()}>Try again</Button></div>;
  const status = query.data;
  const complete = (code: string) => status.steps.some(step => step.code === code && step.status === "COMPLETED");
  const next = stages.find(step => !complete(step.code)) ?? stages[stages.length - 1];
  const active = Math.max(0, stages.findIndex(step => step.code === (params.get("step") || next.code)));
  const selected = stages[active];
  const prior = stages.slice(0, active).find(step => !complete(step.code));
  const locked = !status.onboarding_completed && Boolean(prior) && !complete(selected.code);
  const needsHeadquarters = selected.code === "organization" && status.readiness.issues.some(issue => issue.code === "STRUCTURE_LOCATION");
  const readOnly = complete(selected.code) && selected.code !== "finish" && editing !== selected.code;
  const failure = finish.isError ? normalizeApiError(finish.error) : review.isError ? normalizeApiError(review.error) : null;
  const resetFeedback = (event?: { preventDefault: () => void }) => {
    if (setupEditing?.hasChanges) { event?.preventDefault(); setNavigationNotice(true); return; }
    review.reset(); finish.reset(); setEditing(null); setNavigationNotice(false);
  };
  const laterStepsSaved = !complete(selected.code) && stages.slice(active + 1).some(step => complete(step.code));
  return <div className="sb-journey space-y-5">
    <header className="sb-journey-header">
      <p className="text-sm font-medium text-[var(--accent-text)]">Company setup · {status.onboarding_completed ? `Completed · Step ${active + 1} of ${stages.length}` : `Step ${active + 1} of ${stages.length}`}</p>
      <h1 className="mt-2 text-2xl font-semibold">{compact ? "Build your company workspace" : selected.title}</h1>
      <p className="mt-2 max-w-3xl text-sm text-[var(--muted)]">{compact ? "Set up the structure, prepare access and forms, then invite your people." : selected.description}</p>
      <div role="progressbar" aria-label="Company setup completion" aria-valuenow={status.progress} aria-valuemin={0} aria-valuemax={100} className="sb-journey-progress mt-4"><div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${status.progress}%` }}/></div>
      {compact && <Link href={stepUrl(next.code)} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white">Continue setup<ArrowRight size={18}/></Link>}
    </header>
    {laterStepsSaved && <p className="sb-notice">Your later steps are saved. Complete this missing step to continue.</p>}
    {navigationNotice && setupEditing?.hasChanges && <p role="alert" className="sb-notice sb-notice-warning">Save or discard your changes below before moving to another step.</p>}
    <details key={selected.code} open={!compact} className="sb-disclosure"><summary>All setup steps <span className="sb-count">{stages.filter(step => complete(step.code)).length} of {stages.length} complete</span></summary><nav aria-label="Setup steps" className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-4">{stages.map((step, index) => {
      const unavailable = !status.onboarding_completed && !complete(step.code) && stages.slice(0, index).some(previous => !complete(previous.code));
      return <Link key={step.code} href={stepUrl(step.code)} onClick={resetFeedback} aria-current={!compact && selected.code === step.code ? "step" : undefined} className={"flex items-start gap-3 rounded-xl border p-3 text-sm " + (selected.code === step.code ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "hover:border-teal-500")}>
        {complete(step.code) ? <CheckCircle2 size={18} className="shrink-0 text-teal-700"/> : unavailable ? <LockKeyhole size={18} className="shrink-0 text-neutral-400"/> : <Circle size={18} className="shrink-0 text-[var(--muted)]"/>}<span><strong>{index + 1}. {step.title}</strong><span className="mt-1 block text-xs text-[var(--muted)]">{complete(step.code) ? "Complete · review or edit" : unavailable ? "After earlier steps" : "Ready to continue"}</span></span>
      </Link>;
    })}</nav></details>
    {!compact && <section className="sb-workspace-panel">
      {locked ? <div className="space-y-3"><h2 className="text-lg font-semibold">First, complete {prior?.title.toLowerCase()}</h2><p className="text-sm">This step uses the choices made earlier. Your existing company records are kept.</p><Link href={stepUrl(prior!.code)} onClick={resetFeedback} className="inline-flex rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white">Continue with {prior?.title.toLowerCase()} →</Link></div> : <>
        {readOnly ? <div className="rounded-xl border border-teal-300 p-5"><p className="flex items-center gap-2 font-semibold"><CheckCircle2 size={20} className="text-teal-700"/>Saved and completed</p><p className="mt-2 text-sm">Your saved choices are shown below. Choose Edit when you want to change this step.</p><Button className="mt-4" variant="outline" onClick={() => setEditing(selected.code)}>Edit this step</Button><SetupSavedChoices step={selected.code}/></div> : <div key={selected.code} className="sb-setup-editor space-y-5">
          {selected.code === "company" && <CompanyProfileSection/>}
          {selected.code === "organization" && <HeadquartersWorkspace/>}
          {selected.code === "departments" && <><div className="flex flex-wrap gap-2"><Button variant={structurePart === "departments" ? "primary" : "outline"} onClick={() => setStructurePart("departments")}>Departments</Button><Button variant={structurePart === "teams" ? "primary" : "outline"} onClick={() => setStructurePart("teams")}>Teams (optional)</Button></div>{structurePart === "departments" ? <DepartmentsPage/> : <TeamsPage/>}</>}
          {selected.code === "positions" && <PositionsPage/>}
          {selected.code === "permissions" && <AccessPage/>}
          {selected.code === "forms" && <SetupFormsWorkspace/>}
          {selected.code === "employees" && <InvitationsPage/>}
        </div>}
        {selected.code === "finish" ? <div className="space-y-4"><ul className="space-y-2">{stages.slice(0, -1).map(step => <li key={step.code} className="flex items-center gap-3 rounded-xl border p-3">{complete(step.code) ? <CheckCircle2 size={20} className="shrink-0 text-teal-700"/> : <Circle size={20}/>}<span className="flex-1 text-sm">{step.title}</span><Link className="text-sm underline" href={stepUrl(step.code)} onClick={resetFeedback}>Review</Link></li>)}</ul><p className="text-sm">Pending invitations do not delay activation. You can add more branches, positions and forms later.</p><Button loading={finish.isPending} disabled={!status.readiness.ready || status.onboarding_completed} onClick={() => finish.mutate()}>{status.onboarding_completed ? "Setup completed" : "Activate company workspace"}</Button>{status.onboarding_completed && <Link className="block underline" href="/dashboard">Open dashboard →</Link>}{status.readiness.issues.filter(issue => issue.severity === "ERROR").map(issue => <p key={issue.code} className="text-sm text-amber-700">{issue.message}</p>)}</div> : <div className="sb-step-actions mt-6">
          {!readOnly && <p className="mb-3 text-sm text-[var(--muted)]">{needsHeadquarters ? "Save your headquarters above to continue. Additional branches are optional." : "Save your changes above, then continue. You can add more later."}</p>}
          {setupEditing?.hasChanges && <p role="status" className="sb-help mb-3">You have unfinished changes above. Save or discard them to continue.</p>}
          <div className="flex flex-wrap items-center gap-3">{readOnly ? <Link href={stepUrl(stages[active + 1].code)} onClick={resetFeedback} className="rounded-xl bg-teal-700 px-4 py-3 text-sm font-semibold text-white">Continue to {stages[active + 1].title.toLowerCase()} →</Link> : <Button disabled={needsHeadquarters || setupEditing?.hasChanges} loading={review.isPending} onClick={() => review.mutate(selected.code)}>Confirm step and continue to {stages[active + 1].title.toLowerCase()} →</Button>}
            {!readOnly && selected.code === "departments" && <Button variant="outline" disabled={setupEditing?.hasChanges} loading={review.isPending} onClick={() => review.mutate(selected.code)}>No departments or teams needed</Button>}
            {!readOnly && selected.code === "employees" && <Button variant="outline" disabled={setupEditing?.hasChanges} loading={review.isPending} onClick={() => review.mutate(selected.code)}>Invite people later</Button>}
          </div>
        </div>}
        {failure && <p role="alert" className="mt-4 text-sm text-red-700">{Object.values(failure.fields).join(" ") || failure.message}</p>}
      </>}
      <div className="mt-6 border-t pt-4"><Link className="text-sm underline" href={active > 0 ? stepUrl(stages[active - 1].code) : "/dashboard"} onClick={resetFeedback}>← {active > 0 ? stages[active - 1].title : "Dashboard"}</Link></div>
    </section>}
  </div>;
}

export default function SetupJourney(props: { compact?: boolean }) {
  return <Suspense fallback={<p role="status">Loading setup…</p>}><SetupEditingProvider><SetupJourneyContent {...props}/></SetupEditingProvider></Suspense>;
}
