from pathlib import Path
base=Path('C:/Users/1213/Desktop/Jonathan/business_management_frontend/src')
stage=Path('.notification-fix/workspace-first-look')
text=(base/'components/layout/Sidebar.tsx').read_text(encoding='utf-8')
text=text.replace('  const navigate = () => { setSearch(""); setExpandedGroups({}); onMobileOpenChange(false); };','''  const navigate = () => { setSearch(""); onMobileOpenChange(false); };
  const primaryRoutes = ["/dashboard", "/forms", "/reporting/obligations", "/materials", "/requests", "/approvals", "/company", "/documents", "/analytics", "/settings", "/support"];
  const primary = primaryRoutes.flatMap(href => allNavigation.filter(item => item.href === href));
  const secondary = navigation.filter(item => !primaryRoutes.includes(item.href));''')
text=text.replace('''        {navigation.map((item, index) => {''','''        {!search.trim() && primary.map(item => { const Icon = item.icon; const active = selected?.href === item.href; return <Link key={item.href} href={item.href} onClick={navigate} aria-current={active ? "page" : undefined} className="sb-nav-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium"><Icon className="h-5 w-5 shrink-0" aria-hidden="true"/><span>{item.label}</span></Link>; })}
        <details className="pt-2" open={search.trim() ? true : undefined}><summary className="sb-nav-heading min-h-11 cursor-pointer">{search.trim() ? "Search results" : "More workspace pages"}</summary>
        {(search.trim() ? navigation : secondary).map((item, index, listed) => {''')
text=text.replace('const expanded = Boolean(search.trim()) || (expandedGroups[section] ?? (sectionActive || section === "Overview"));','const expanded = Boolean(search.trim()) || (expandedGroups[section] ?? (sectionActive || section === "Overview"));')
text=text.replace('sectionFor(navigation[index-1].href)', 'sectionFor(listed[index-1].href)')
text=text.replace('''        })}
      </nav>''','''        })}
        </details>
      </nav>''')
(stage/'Sidebar.tsx').write_text(text,encoding='utf-8')
text=(base/'components/layout/navigation.ts').read_text(encoding='utf-8')
for old,new in [('label: "Overview"','label: "Home"'),('label: "Directory"','label: "People"'),('label: "Analytics"','label: "Charts & insights"'),('label: "Approvals"','label: "Reviews"'),('label: "Company settings"','label: "Company administration"')]: text=text.replace(old,new)
(stage/'navigation.ts').write_text(text,encoding='utf-8')
text=(base/'app/(dashboard)/analytics/page.tsx').read_text(encoding='utf-8').replace('title="Analytics"','title="Charts & insights"').replace('Understand form submissions, request decisions and activity trends within your authorised scope.','Explore company activity, saved form entries and request decisions available to you.').replace('No analytics are available for your authorized scope.','No activity summaries are available to your account yet.')
(stage/'analytics-page.tsx').write_text(text,encoding='utf-8')
text=(base/'app/(dashboard)/settings/page.tsx').read_text(encoding='utf-8').replace('title="Company settings" description="Choose the part of your company you want to update."','title="Company administration" description="Manage your company structure, people, forms and preferences in one place."').replace('Company form library','Company forms & library')
(stage/'settings-page.tsx').write_text(text,encoding='utf-8')
text=(base/'app/globals.css').read_text(encoding='utf-8')
text+='''
/* Company overview: welcoming surfaces and compact, readable daily work. */
.sb-home-hero { position: relative; isolation: isolate; overflow: hidden; display: flex; flex-wrap: wrap; align-items: flex-start; gap: 1.5rem; padding: clamp(1.25rem, 3vw, 2rem); border: 1px solid var(--line); border-radius: 1.5rem; background: linear-gradient(115deg, var(--surface), color-mix(in srgb, var(--accent-soft) 70%, var(--surface))); box-shadow: var(--panel-shadow); }
.sb-home-hero::after { content: ''; position: absolute; z-index: -1; right: -3rem; bottom: -7rem; width: 20rem; height: 20rem; border: 2rem solid color-mix(in srgb, var(--accent) 7%, transparent); border-radius: 50%; pointer-events: none; }
.sb-home-shortcut { display: flex; align-items: flex-start; gap: .75rem; min-width: 0; padding: .9rem; border: 1px solid var(--line); border-radius: .85rem; transition: border-color 150ms, background-color 150ms; }
.sb-home-shortcut:hover { background: var(--surface-hover); border-color: var(--accent); }
.sb-home-shortcut-icon, .sb-chart-icon { display: inline-flex; flex-shrink: 0; align-items: center; justify-content: center; padding: .6rem; border-radius: .8rem; background: var(--accent-soft); color: var(--accent-text); }
.sb-home-metric { min-width: 0; position: relative; padding: 1.1rem; border: 1px solid var(--line); border-radius: 1rem; background: var(--surface); box-shadow: var(--panel-shadow); }
.sb-home-metric::before { content: ''; position: absolute; inset: 1rem auto 1rem 0; width: 3px; border-radius: 3px; background: var(--accent); }
.sb-chart-panel { min-width: 0; padding: 1.25rem; border: 1px solid var(--line); border-radius: 1rem; background: var(--surface); box-shadow: var(--panel-shadow); color: var(--ink); }
.sb-chart-empty { display: flex; min-height: 10rem; flex-direction: column; align-items: center; justify-content: center; gap: .5rem; margin-top: 1rem; border-radius: .85rem; background: var(--surface-soft); text-align: center; padding: 1rem; color: var(--muted); }
.sb-chart-empty p { font-size: .9rem; font-weight: 600; color: var(--ink); }
.sb-chart-empty span { max-width: 30ch; font-size: .8rem; }
@media (max-width: 639px) { .sb-home-hero h1 { font-size: 1.75rem; } .sb-home-hero .sb-primary-link { width: 100%; } .sb-home-metric { padding: .9rem; } .sb-chart-panel { padding: 1rem; } }
@media (prefers-reduced-motion: reduce) { .sb-home-shortcut { transition: none; } }
'''
(stage/'globals.css').write_text(text,encoding='utf-8')