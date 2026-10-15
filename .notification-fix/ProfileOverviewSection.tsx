import type { AuthUser } from "@/types/auth";
import { formatEnumLabel } from "@/utils/format";


export default function ProfileOverviewSection({
  user,
}: {
  user: AuthUser;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">

      <h2 className="text-lg font-semibold text-gray-950">
        Profile
      </h2>


      <dl className="mt-6 grid gap-5 sm:grid-cols-2">

        <ProfileField
          label="Full name"
          value={
            user.full_name
          }
        />

        <ProfileField
          label="Email"
          value={
            user.email
          }
        />

        <ProfileField
          label="Account role"
          value={
            formatEnumLabel(user.role)
          }
        />

        <ProfileField
          label="Position"
          value={
            user.position_name || "Not assigned"
          }
        />

        <ProfileField
          label="Company"
          value={
            user.company_name || (user.company ? "Company member" : "Not assigned")
          }
        />

        <ProfileField
          label="Branch"
          value={
            user.branch_name || (user.branch ? "Branch assigned" : "Not assigned")
          }
        />
      </dl>
    </section>
  );
}


function ProfileField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-gray-400">
        {label}
      </dt>

      <dd className="mt-1 break-words text-sm font-medium text-gray-900">
        {value}
      </dd>
    </div>
  );
}
