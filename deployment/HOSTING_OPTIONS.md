# Staging hosting options

Research date: 15 October 2026. User preference: lowest practical staging cost, with no region requirement. No provider or spending commitment has been selected. These are options for synthetic-data staging, not a production capacity estimate.

## Budget-first recommendation

Check the month-to-month quote for **OVHcloud VPS-2** first, then compare **Hetzner CX33**. Use an available European location with synthetic data; there is no user-required region. Both should be evaluated as self-managed servers. Do not purchase an annual commitment merely to obtain the lowest advertised monthly equivalent during a short staging exercise.

OVHcloud's worldwide page currently advertises VPS-2 with 4 vCores, 8 GB RAM and 75 GB NVMe from $8.50/month. Its Configure link selects `pricing=upfront12`, indicating annual upfront pricing; the configurator's actual totals were not exposed in the retrieved page. The $8.50 figure is therefore **not a verified month-to-month or all-in quote**. Review billing country, commitment, first payment, renewal price, tax and optional extras before purchasing. [Published specifications/pricing](https://www.ovhcloud.com/en/vps/), [advertised configuration link](https://www.ovhcloud.com/en/vps/configurator/?brick=VPS%2BModel%2B2&planCode=vps-2027-model2&pricing=upfront12&processor=+&storage=75__SSD__NVMe&vcore=4__vCore).

Hetzner remains worth checking because it offers the matching 8 GB CX33, but its current price was not verifiable from the retrieved page. Netcup's retrieved VPS 1000 G12.5 listing showed 8 GB with a 12-month term and a higher monthly equivalent; it is not the first choice for a short low-cost staging period. [Netcup listing](https://www.netcup.com/en/server/vps). The $48 DigitalOcean baseline below is no longer the budget-first recommendation.

Keep initial service costs down with a private R2 Standard staging bucket within its included usage and Mailtrap's limited free Email Sandbox for a small smoke test. These allowances do not eliminate domain, off-host backup or excess usage costs. A sandbox does not prove real inbox deliverability. The final spending ceiling should be set from the actual checkout quote, not the marketing starting price.

## Suggested layout

Start with one Linux virtual machine for the backend, worker, scheduler, PostgreSQL, Redis, ClamAV and HTTPS proxy. Deploy the frontend separately or run its built server on that host after checking available memory. Keep the existing staging Compose stack and private network boundaries. Use separate private object storage and a test email sandbox. Neither VM option below manages the application, operating-system updates or recovery procedures for us.

An 8 GiB machine with roughly four shared CPU cores is a starting estimate for light staging use. Measure actual memory during signature reloads, migrations, job execution and uploads before accepting it. Build the frontend outside the running staging stack if builds compete for memory. Increase capacity if measurement requires it; do not disable scanning to fit a smaller machine.

ClamAV's official Docker guidance states a 3 GiB minimum and 4 GiB preferred allocation for the scanner alone: [memory requirements](https://docs.clamav.net/manual/Installing/Docker.html). The combined-stack estimate above is our engineering inference, not a vendor guarantee.

## Compute comparison

| Option | Verified listed specification | Price evidence | Decision use |
| --- | --- | --- | --- |
| DigitalOcean Basic, regular CPU | 8 GiB RAM, 4 vCPUs, 160 GiB SSD | $48/month listed compute price | Clear published baseline if that budget is comfortable |
| Hetzner CX33 | 8 GB RAM, 4 shared vCPUs, 80 GB NVMe | Exact current price was not exposed in the retrieved pricing page; confirm in checkout | Compare the live quote if minimizing cost matters; confirm regional capacity |
| OVHcloud VPS-2 | 8 GB RAM, 4 vCores, 75 GB NVMe | From $8.50/month advertised; linked configuration selects annual upfront pricing | First budget quote to check, with month-to-month terms preferred for staging |

Sources: [DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets), [Hetzner cost-optimized cloud](https://www.hetzner.com/cloud/cost-optimized/). Hetzner's [primary IPv4 pricing](https://docs.hetzner.com/general/infrastructure-and-availability/ipv4-pricing/) is separate. Do not treat an old plan price or an advertised starting price as the quote for the selected server. Availability and account eligibility must be confirmed during signup.

The $48 DigitalOcean figure is compute only. Allow separately for applicable tax, domain registration, off-host backup retention, storage/API usage and any paid email plan. No all-in price is quoted. Follow the budget-first shortlist above; no automatic purchase is authorized.

## File storage

Cloudflare R2 Standard is an S3-compatible candidate for the existing storage adapter. It lists 10 GB-month storage, 1 million Class A operations and 10 million Class B operations per month in the free tier. Beyond included usage, Standard storage is $0.015/GB-month, with operation charges; internet egress is listed as free. This does not make the entire staging environment free. [Current pricing](https://developers.cloudflare.com/r2/pricing/), [S3-compatible service](https://developers.cloudflare.com/r2/how-r2-works/).

Use a staging-only bucket and bucket-scoped credentials. Keep public access disabled. Verify actual write/read/delete, authenticated download, anonymous denial and backup listing against the adapter; S3 compatibility alone does not prove all application operations. If regional storage is required, verify the chosen product's location guarantees before using it; do not infer residency from the VM's region.

## Test email

Mailtrap Email Sandbox is a candidate for capturing OTP, invitation and reset messages without delivery to real recipients. Its published free sandbox tier has 50 test emails/month, one sandbox and retention of 10 messages at once. That is suitable only for a small initial smoke test; repeated multi-user journeys may need a larger plan. [Pricing](https://mailtrap.io/pricing/), [SMTP integration](https://docs.mailtrap.io/email-sandbox/setup/sandbox-smtp-integration).

Use SMTP details from the sandbox's integration screen, with TLS, in the protected staging environment. A captured message verifies application-to-sandbox delivery, not delivery to Gmail/Outlook or another real mailbox. After sandbox checks, separately test approved test-recipient inbox delivery using a verified sending domain and a sending service; the sandbox and transactional-sending products are different.

## Account setup order

1. The owner creates the chosen provider account, completes any identity/billing checks and reviews the actual VM quote. Do not provision until the cost and region are approved.
2. Create an isolated staging project, restricted server access and budget alerts. Record the server's OS, architecture and address without sharing credentials in chat.
3. Use a domain/subdomains the owner controls for the app and API; domain ownership is not assumed here. Configure DNS and HTTPS for the chosen host.
4. Create the private staging bucket and email sandbox. Enter their secrets on the host through a protected environment/secret store.
5. Follow [STAGING.md](STAGING.md): preflight, image review/build, migrations, scanner tests, startup, role journeys and isolated restore drill.

No accounts, servers, DNS records, buckets or mail services were created in this research step. No credentials were requested or transmitted. Actual provisioning and paid services remain owner decisions.
